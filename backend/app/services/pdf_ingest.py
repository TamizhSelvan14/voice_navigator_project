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
    def __init__(self, chunk_size: int = 900, overlap: int = 150):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def infer_domain(self, pdf_path: Path) -> str:
        name = pdf_path.name.lower()
        if 'driver' in name or 'dmv' in name or 'handbook' in name:
            return 'DMV'
        return 'ESG'

    def clean_text(self, text: str) -> str:
        text = text.replace('\u00a0', ' ')
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def chunk_text(self, text: str) -> Iterable[str]:
        if not text:
            return []
        start = 0
        chunks: List[str] = []
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= len(text):
                break
            start = max(end - self.overlap, 0)
        return chunks

    def ingest_pdf(self, pdf_path: Path) -> List[ChunkRecord]:
        records: List[ChunkRecord] = []
        domain = self.infer_domain(pdf_path)
        doc = fitz.open(pdf_path)
        for page_index in range(len(doc)):
            page = doc[page_index]
            text = self.clean_text(page.get_text('text'))
            if not text:
                continue
            section = text[:80].split('.')[:1][0].strip() or f'Page {page_index + 1}'
            for chunk_num, chunk in enumerate(self.chunk_text(text)):
                records.append(
                    ChunkRecord(
                        chunk_id=f'{pdf_path.stem}-p{page_index + 1}-c{chunk_num}',
                        domain=domain,
                        source=pdf_path.name,
                        page=page_index + 1,
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
