from __future__ import annotations

import json
from dataclasses import asdict

from app.config import settings
from app.services.pdf_ingest import PdfIngester
from app.services.vector_store import VectorStore


def main() -> None:
    settings.processed_data_dir.mkdir(parents=True, exist_ok=True)
    settings.assets_dir.mkdir(parents=True, exist_ok=True)

    ingester = PdfIngester()
    chunks = ingester.ingest_folder(settings.raw_data_dir, settings.assets_dir)
    chunk_path = settings.processed_data_dir / 'chunks.jsonl'
    ingester.save_chunks(chunks, chunk_path)

    payload = [asdict(item) for item in chunks]
    store = VectorStore()
    store.build(payload)

    # Stats
    type_counts = {}
    for item in chunks:
        t = item.obj_type
        type_counts[t] = type_counts.get(t, 0) + 1

    print(f'\nIndexed {len(payload)} chunks from {len({item.source for item in chunks})} documents.')
    print(f'Types: {type_counts}')
    print(f'Assets: {len(list(settings.assets_dir.iterdir()))} files')
    print(f'Chunk file: {chunk_path}')
    print(f'Vector index: {settings.processed_data_dir / "vector.index"}')


if __name__ == '__main__':
    main()
