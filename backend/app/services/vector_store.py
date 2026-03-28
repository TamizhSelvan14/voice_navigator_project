from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import settings


class VectorStore:
    def __init__(self, processed_dir: Path | None = None):
        self.processed_dir = processed_dir or settings.processed_data_dir
        self.model = SentenceTransformer(settings.embedding_model)
        self.index_path = self.processed_dir / 'vector.index'
        self.metadata_path = self.processed_dir / 'metadata.json'
        self.index = None
        self.metadata: List[Dict] = []

    def build(self, chunks: List[Dict]) -> None:
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        texts = [item['text'] for item in chunks]
        embeddings = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
        matrix = np.array(embeddings, dtype='float32')
        index = faiss.IndexFlatIP(matrix.shape[1])
        index.add(matrix)
        faiss.write_index(index, str(self.index_path))
        with self.metadata_path.open('w', encoding='utf-8') as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)
        self.index = index
        self.metadata = chunks

    def load(self) -> None:
        if not self.index_path.exists() or not self.metadata_path.exists():
            raise FileNotFoundError('Vector index not found. Run scripts/ingest_documents.py first.')
        self.index = faiss.read_index(str(self.index_path))
        self.metadata = json.loads(self.metadata_path.read_text(encoding='utf-8'))

    def ensure_loaded(self) -> None:
        if self.index is None or not self.metadata:
            self.load()

    def search(self, question: str, mode: str, top_k: int) -> List[Tuple[Dict, float]]:
        self.ensure_loaded()
        query = self.model.encode([question], normalize_embeddings=True)
        q = np.array(query, dtype='float32')
        scores, indices = self.index.search(q, min(max(top_k * 4, top_k), len(self.metadata)))
        results: List[Tuple[Dict, float]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            item = self.metadata[idx]
            if item['domain'] != mode:
                continue
            results.append((item, float(score)))
            if len(results) >= top_k:
                break
        return results
