from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List

import fitz


@dataclass
class ChunkRecord:
    chunk_id: str
    domain: str
    source: str
    page: int
    section: str
    text: str


class PdfIngester:
    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def infer_domain(self, pdf_path: Path) -> str:
        name = pdf_path.name.lower()
        if 'driver' in name or 'dmv' in name or 'handbook' in name:
            return 'DMV'
        return 'ESG'

    def clean_text(self, text: str) -> str:
        text = text.replace('\u00a0', ' ')
        text = re.sub(r'[ \t]+', ' ', text)           # collapse horizontal whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)        # max 2 newlines
        text = re.sub(r' *\n *', '\n', text)           # trim around newlines
        return text.strip()

    def _find_sentence_boundary(self, text: str, pos: int) -> int:
        """Find the nearest sentence boundary (. ! ? \\n) near pos."""
        window = 80
        search_start = max(pos - window, 0)
        search_end = min(pos + window, len(text))
        snippet = text[search_start:search_end]

        # Look for sentence endings near the target position
        best = -1
        for m in re.finditer(r'[.!?]\s', snippet):
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

            # Try to break at a sentence boundary
            if end < len(text):
                end = self._find_sentence_boundary(text, end)

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= len(text):
                break
            start = max(end - self.overlap, start + 1)
        return chunks

    def ingest_pdf(self, pdf_path: Path) -> List[ChunkRecord]:
        records: List[ChunkRecord] = []
        domain = self.infer_domain(pdf_path)
        doc = fitz.open(pdf_path)

        # Accumulate text across pages for better cross-page context
        full_text_pages: List[tuple[int, str]] = []
        for page_index in range(len(doc)):
            page = doc[page_index]
            text = self.clean_text(page.get_text('text'))
            if text:
                full_text_pages.append((page_index + 1, text))

        # Chunk per page (preserves page-level citation accuracy)
        for page_num, text in full_text_pages:
            section = text[:100].split('.')[0].strip() or f'Page {page_num}'
            for chunk_num, chunk in enumerate(self.chunk_text(text)):
                records.append(
                    ChunkRecord(
                        chunk_id=f'{pdf_path.stem}-p{page_num}-c{chunk_num}',
                        domain=domain,
                        source=pdf_path.name,
                        page=page_num,
                        section=section,
                        text=chunk,
                    )
                )
        return records

    def ingest_folder(self, raw_dir: Path) -> List[ChunkRecord]:
        all_records: List[ChunkRecord] = []
        for pdf_path in sorted(raw_dir.glob('*.pdf')):
            all_records.extend(self.ingest_pdf(pdf_path))
        return all_records

    def save_chunks(self, chunks: List[ChunkRecord], output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open('w', encoding='utf-8') as f:
            for item in chunks:
                f.write(json.dumps(asdict(item), ensure_ascii=False) + '\n')
