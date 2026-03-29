from __future__ import annotations

import base64
import contextlib
import hashlib
import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional

import fitz  # PyMuPDF
import requests
from PIL import Image
import io

from app.config import settings

# Suppress noisy MuPDF structure-tree warnings – they come out on the native
# stderr file descriptor and cannot be silenced via TOOLS alone.
fitz.TOOLS.mupdf_display_warnings(False)
fitz.TOOLS.mupdf_display_errors(False)


@contextlib.contextmanager
def _suppress_mupdf_stderr():
    """Redirect fd-level stderr to /dev/null to swallow MuPDF C-level messages."""
    devnull_fd = os.open(os.devnull, os.O_WRONLY)
    old_stderr_fd = os.dup(2)
    try:
        os.dup2(devnull_fd, 2)
        yield
    finally:
        os.dup2(old_stderr_fd, 2)
        os.close(old_stderr_fd)
        os.close(devnull_fd)

# ─── data class ───────────────────────────────────────────────────────

@dataclass
class ChunkRecord:
    chunk_id: str
    domain: str
    source: str
    page: int
    section: str
    text: str
    obj_type: str = "text"          # text | table | chart | image
    image_path: Optional[str] = None  # relative path inside assets/


# ─── helpers ──────────────────────────────────────────────────────────

def _page_to_b64(page: fitz.Page, dpi: int = 150) -> tuple[str, bytes]:
    """Render a fitz page -> (base64 jpeg, raw bytes)."""
    pix = page.get_pixmap(dpi=dpi)
    img_bytes = pix.tobytes("jpeg")
    return base64.b64encode(img_bytes).decode("ascii"), img_bytes


def _call_nemotron_parse(b64_img: str, mime: str = "image/jpeg") -> str:
    """Send an image to nvidia/nemotron-parse and return markdown."""
    headers = {
        "Authorization": f"Bearer {settings.next_api_key()}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    content = f'<img src="data:{mime};base64,{b64_img}" />'
    payload = {
        "model": settings.parse_model,
        "messages": [{"role": "user", "content": content}],
        "tools": [{"type": "function", "function": {"name": "markdown_no_bbox"}}],
        "tool_choice": {"type": "function", "function": {"name": "markdown_no_bbox"}},
        "max_tokens": 8192,
    }
    for attempt in range(4):
        try:
            resp = requests.post(
                settings.nvidia_parse_url,
                headers=headers,
                json=payload,
                timeout=120,
            )
            resp.raise_for_status()
            body = resp.json()
            # extract markdown from tool call
            choices = body.get("choices", [])
            if choices:
                msg = choices[0].get("message", {})
                tool_calls = msg.get("tool_calls", [])
                if tool_calls:
                    raw_args = tool_calls[0].get("function", {}).get("arguments", "[]")
                    parsed = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                    # nemotron-parse returns a list of {"text": "..."} objects
                    if isinstance(parsed, list):
                        parts = []
                        for item in parsed:
                            if isinstance(item, dict):
                                parts.append(item.get("text", item.get("markdown", "")))
                            elif isinstance(item, str):
                                parts.append(item)
                        return "\n\n".join(parts)
                    elif isinstance(parsed, dict):
                        return parsed.get("markdown", parsed.get("text", ""))
                    else:
                        return str(parsed)
                # fallback: plain content
                return msg.get("content", "")
            return ""
        except (requests.HTTPError, requests.ConnectionError, ConnectionResetError) as e:
            if attempt < 3:
                wait = 5 * (attempt + 1)
                print(f"        Parse retry {attempt+1}/4, waiting {wait}s... ({type(e).__name__})")
                time.sleep(wait)
                continue
            raise
    return ""


def _crop_region(
    page: fitz.Page,
    bbox: dict,
    assets_dir: Path,
    chunk_id: str,
) -> Optional[str]:
    """Crop a bounding box from a page and save as PNG. Returns relative path."""
    try:
        x0 = bbox.get("x0", bbox.get("x_min", 0))
        y0 = bbox.get("y0", bbox.get("y_min", 0))
        x1 = bbox.get("x1", bbox.get("x_max", 0))
        y1 = bbox.get("y1", bbox.get("y_max", 0))
        if x1 <= x0 or y1 <= y0:
            return None
        rect = fitz.Rect(x0, y0, x1, y1)
        pix = page.get_pixmap(clip=rect, dpi=200)
        fname = f"{chunk_id}.png"
        out = assets_dir / fname
        pix.save(str(out))
        return fname
    except Exception:
        return None


# ─── main class ───────────────────────────────────────────────────────

class PdfIngester:
    """Multimodal PDF ingester using nemotron-parse + fallback text."""

    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        self.chunk_size = chunk_size
        self.overlap = overlap

    # ── domain detection ──────────────────────────────────────────

    def infer_domain(self, pdf_path: Path) -> str:
        name = pdf_path.name.lower()
        if "driver" in name or "dmv" in name or "handbook" in name:
            return "DMV"
        return "ESG"

    # ── text cleaning ─────────────────────────────────────────────

    def clean_text(self, text: str) -> str:
        text = text.replace("\u00a0", " ")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" *\n *", "\n", text)
        return text.strip()

    # ── chunking ──────────────────────────────────────────────────

    def _find_sentence_boundary(self, text: str, pos: int) -> int:
        window = 80
        search_start = max(pos - window, 0)
        search_end = min(pos + window, len(text))
        snippet = text[search_start:search_end]
        best = -1
        for m in re.finditer(r"[.!?]\s", snippet):
            candidate = search_start + m.end()
            if candidate <= pos + window:
                best = candidate
        if best > 0 and abs(best - pos) < window:
            return best
        return pos

    def chunk_text(self, text: str) -> Iterable[str]:
        if not text:
            return []
        start = 0
        chunks: List[str] = []
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            if end < len(text):
                end = self._find_sentence_boundary(text, end)
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= len(text):
                break
            start = max(end - self.overlap, start + 1)
        return chunks

    # ── markdown block splitter ───────────────────────────────────

    def _split_markdown_blocks(self, md: str) -> List[dict]:
        """Split nemotron-parse markdown into typed blocks."""
        blocks: List[dict] = []
        current_text = []
        in_table = False
        table_lines = []

        for raw_line in md.split("\n"):
            line = raw_line.strip()

            # detect table rows
            if line.startswith("|") and line.endswith("|"):
                if current_text:
                    blocks.append({"type": "text", "content": "\n".join(current_text)})
                    current_text = []
                if not in_table:
                    in_table = True
                    table_lines = []
                table_lines.append(line)
                continue

            if in_table:
                # table ended
                blocks.append({"type": "table", "content": "\n".join(table_lines)})
                table_lines = []
                in_table = False

            # detect image references (chart/figure)
            if line.startswith("![") or line.startswith("<img"):
                if current_text:
                    blocks.append({"type": "text", "content": "\n".join(current_text)})
                    current_text = []
                blocks.append({"type": "chart", "content": line})
                continue

            current_text.append(raw_line)

        # flush
        if in_table and table_lines:
            blocks.append({"type": "table", "content": "\n".join(table_lines)})
        if current_text:
            blocks.append({"type": "text", "content": "\n".join(current_text)})

        return blocks

    # ── page-level image capture ──────────────────────────────────

    def _extract_page_images(
        self,
        page: fitz.Page,
        page_num: int,
        pdf_stem: str,
        domain: str,
        source: str,
        assets_dir: Path,
    ) -> List[ChunkRecord]:
        """Extract embedded images AND render a full-page snapshot for vector charts."""
        records: List[ChunkRecord] = []

        # ── embedded XObject images (raster figures) ─────────────
        images = page.get_images(full=True)
        for img_idx, img_info in enumerate(images):
            xref = img_info[0]
            try:
                base_image = page.parent.extract_image(xref)
                if not base_image or len(base_image.get("image", b"")) < 2000:
                    continue  # skip tiny images (icons, bullets)
                img_bytes = base_image["image"]
                ext = base_image.get("ext", "png")
                chunk_id = f"{pdf_stem}-p{page_num}-img{img_idx}"
                fname = f"{chunk_id}.{ext}"
                (assets_dir / fname).write_bytes(img_bytes)
                records.append(ChunkRecord(
                    chunk_id=chunk_id,
                    domain=domain,
                    source=source,
                    page=page_num,
                    section=f"Image from page {page_num}",
                    text=f"[Image from {source}, page {page_num}]",
                    obj_type="image",
                    image_path=fname,
                ))
            except Exception:
                continue

        # ── vector-drawn charts (not captured as XObjects) ────────
        # Render the full page at higher DPI and save as an asset when the page
        # has substantial vector drawings but no embedded raster images.
        if not records:
            try:
                drawings = page.get_drawings()
                if len(drawings) > 10:  # likely a chart/diagram page
                    pix = page.get_pixmap(dpi=200)
                    fname = f"{pdf_stem}-p{page_num}-render.jpg"
                    pix.pil_save(str(assets_dir / fname), format="JPEG", quality=90)
                    records.append(ChunkRecord(
                        chunk_id=f"{pdf_stem}-p{page_num}-vrender",
                        domain=domain,
                        source=source,
                        page=page_num,
                        section=f"Chart/Figure on page {page_num}",
                        text=f"[Visual chart or figure from {source}, page {page_num}]",
                        obj_type="chart",
                        image_path=fname,
                    ))
            except Exception:
                pass

        return records

    # ── main ingestion ────────────────────────────────────────────

    def ingest_pdf(self, pdf_path: Path, assets_dir: Path) -> List[ChunkRecord]:
        records: List[ChunkRecord] = []
        domain = self.infer_domain(pdf_path)
        with _suppress_mupdf_stderr():
            doc = fitz.open(pdf_path)
        total_pages = len(doc)

        for page_index in range(total_pages):
            page = doc[page_index]
            page_num = page_index + 1
            print(f"    Page {page_num}/{total_pages}")

            # ── Step 1: Try nemotron-parse ────────────────────────
            parsed_md = ""
            page_img_bytes: Optional[bytes] = None
            try:
                b64_img, page_img_bytes = _page_to_b64(page)
                parsed_md = _call_nemotron_parse(b64_img)
            except Exception as e:
                print(f"      nemotron-parse failed for page {page_num}: {e}")

            # ── Step 2: Fallback to PyMuPDF text if parse failed ──
            if not parsed_md or len(parsed_md.strip()) < 20:
                with _suppress_mupdf_stderr():
                    raw_text = self.clean_text(page.get_text("text"))
                if raw_text:
                    for chunk_num, chunk in enumerate(self.chunk_text(raw_text)):
                        section = chunk[:100].split(".")[0].strip() or f"Page {page_num}"
                        records.append(ChunkRecord(
                            chunk_id=f"{pdf_path.stem}-p{page_num}-c{chunk_num}",
                            domain=domain,
                            source=pdf_path.name,
                            page=page_num,
                            section=section,
                            text=chunk,
                            obj_type="text",
                        ))
            else:
                # ── Step 3: Split parsed markdown into blocks ─────
                blocks = self._split_markdown_blocks(parsed_md)
                for blk_idx, block in enumerate(blocks):
                    obj_type = block["type"]
                    content = self.clean_text(block["content"])
                    if len(content) < 10:
                        continue

                    if obj_type == "text":
                        for chunk_num, chunk in enumerate(self.chunk_text(content)):
                            section = chunk[:100].split(".")[0].strip() or f"Page {page_num}"
                            records.append(ChunkRecord(
                                chunk_id=f"{pdf_path.stem}-p{page_num}-b{blk_idx}-c{chunk_num}",
                                domain=domain,
                                source=pdf_path.name,
                                page=page_num,
                                section=section,
                                text=chunk,
                                obj_type="text",
                            ))
                    else:
                        # table or chart: keep as single chunk and save page image as evidence
                        chunk_id = f"{pdf_path.stem}-p{page_num}-{obj_type}{blk_idx}"
                        # Save the rendered page JPEG as the visual evidence asset
                        page_img_fname: Optional[str] = None
                        if page_img_bytes:
                            page_img_fname = f"{chunk_id}.jpg"
                            (assets_dir / page_img_fname).write_bytes(page_img_bytes)
                        records.append(ChunkRecord(
                            chunk_id=chunk_id,
                            domain=domain,
                            source=pdf_path.name,
                            page=page_num,
                            section=f"{obj_type.title()} on page {page_num}",
                            text=content,
                            obj_type=obj_type,
                            image_path=page_img_fname,
                        ))

            # ── Step 4: Extract embedded images (charts/figures) ──
            img_records = self._extract_page_images(
                page, page_num, pdf_path.stem, domain, pdf_path.name, assets_dir,
            )
            records.extend(img_records)

            # rate-limit courtesy for parse API (3 keys in rotation → shorter delay)
            time.sleep(1.5)

        return records

    def ingest_folder(self, raw_dir: Path, assets_dir: Path) -> List[ChunkRecord]:
        all_records: List[ChunkRecord] = []
        assets_dir.mkdir(parents=True, exist_ok=True)
        for pdf_path in sorted(raw_dir.glob("*.pdf")):
            print(f"  Parsing: {pdf_path.name}")
            all_records.extend(self.ingest_pdf(pdf_path, assets_dir))
        return all_records

    def save_chunks(self, chunks: List[ChunkRecord], output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            for item in chunks:
                f.write(json.dumps(asdict(item), ensure_ascii=False) + "\n")
