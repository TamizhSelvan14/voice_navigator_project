from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, List, Tuple

import faiss
import numpy as np
from openai import OpenAI

from app.config import settings


class VectorStore:
    def __init__(self, processed_dir: Path | None = None):
        self.processed_dir = processed_dir or settings.processed_data_dir
        self.client = OpenAI(
            api_key=settings.nvidia_api_key,
            base_url=settings.nvidia_base_url,
        )
        self.index_path = self.processed_dir / "vector.index"
        self.metadata_path = self.processed_dir / "metadata.json"
        self.index = None
        self.metadata: List[Dict] = []
        self._dim: int | None = None

    # ── embedding helpers ──────────────────────────────────────────────

    def _embed_batch(self, texts: List[str], input_type: str) -> np.ndarray:
        """Call NVIDIA embedding API for a single batch."""
        resp = self.client.embeddings.create(
            input=texts,
            model=settings.embedding_model,
            encoding_format="float",
            extra_body={"input_type": input_type, "truncate": "END"},
        )
        vecs = [d.embedding for d in sorted(resp.data, key=lambda d: d.index)]
        return np.array(vecs, dtype="float32")

    def embed_texts(self, texts: List[str], input_type: str = "passage") -> np.ndarray:
        """Embed a list of texts in batches via NVIDIA API."""
        bs = settings.embedding_batch_size
        all_vecs: List[np.ndarray] = []
        total = len(texts)
        for start in range(0, total, bs):
            batch = texts[start : start + bs]
            print(f"  Embedding batch {start // bs + 1}/{(total + bs - 1) // bs}  ({len(batch)} texts)")
            vecs = self._embed_batch(batch, input_type)
            all_vecs.append(vecs)
            if start + bs < total:
                time.sleep(0.15)  # light rate-limit courtesy
        return np.vstack(all_vecs)

    def embed_query(self, text: str) -> np.ndarray:
        return self._embed_batch([text], input_type="query")

    # ── index build / load ─────────────────────────────────────────────

    def build(self, chunks: List[Dict]) -> None:
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        texts = [item["text"] for item in chunks]

        matrix = self.embed_texts(texts, input_type="passage")
        # L2-normalize so inner-product == cosine similarity
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1
        matrix = matrix / norms

        index = faiss.IndexFlatIP(matrix.shape[1])
        index.add(matrix)
        faiss.write_index(index, str(self.index_path))

        with self.metadata_path.open("w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)

        self.index = index
        self.metadata = chunks
        self._dim = matrix.shape[1]
        print(f"  FAISS index built: {matrix.shape[0]} vectors × {matrix.shape[1]} dims")

    def load(self) -> None:
        if not self.index_path.exists() or not self.metadata_path.exists():
            raise FileNotFoundError("Vector index not found. Run scripts/ingest_documents.py first.")
        self.index = faiss.read_index(str(self.index_path))
        self.metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))

    def ensure_loaded(self) -> None:
        if self.index is None or not self.metadata:
            self.load()

    # ── search ─────────────────────────────────────────────────────────

    def search(self, question: str, mode: str, top_k: int) -> List[Tuple[Dict, float]]:
        self.ensure_loaded()

        q = self.embed_query(question)
        norms = np.linalg.norm(q, axis=1, keepdims=True)
        norms[norms == 0] = 1
        q = q / norms

        search_k = min(len(self.metadata), max(top_k * 100, 500))
        scores, indices = self.index.search(q, search_k)

        results: List[Tuple[Dict, float]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            item = self.metadata[idx]
            if item["domain"] != mode:
                continue
            results.append((item, float(score)))
            if len(results) >= top_k:
                break

        return results