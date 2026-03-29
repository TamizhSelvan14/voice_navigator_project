from __future__ import annotations

from typing import Dict, List, Tuple

import httpx

from app.config import settings

RERANK_URL = "https://ai.api.nvidia.com/v1/retrieval/nvidia/llama-nemotron-rerank-1b-v2/reranking"


class Reranker:
    def __init__(self) -> None:
        self.headers = {
            "Authorization": f"Bearer {settings.next_api_key()}",
            "Accept": "application/json",
        }

    def rerank(
        self,
        query: str,
        hits: List[Tuple[Dict, float]],
        top_k: int | None = None,
    ) -> List[Tuple[Dict, float]]:
        if not hits:
            return []
        k = top_k or settings.rerank_top_k

        passages = [{"text": item["text"][:1024]} for item, _score in hits]
        payload = {
            "model": settings.reranker_model,
            "query": {"text": query},
            "passages": passages,
        }

        with httpx.Client(timeout=30) as client:
            self.headers["Authorization"] = f"Bearer {settings.next_api_key()}"
            resp = client.post(RERANK_URL, headers=self.headers, json=payload)
            resp.raise_for_status()
            body = resp.json()

        rankings = sorted(body.get("rankings", []), key=lambda r: r["logit"], reverse=True)

        reranked: List[Tuple[Dict, float]] = []
        for rank in rankings[:k]:
            idx = rank["index"]
            item, _old_score = hits[idx]
            reranked.append((item, float(rank["logit"])))

        return reranked
