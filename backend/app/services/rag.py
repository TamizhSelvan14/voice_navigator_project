from __future__ import annotations

from typing import List

from app.config import settings
from app.schemas import AskResponse, Citation
from app.services.llm import LlmService
from app.services.vector_store import VectorStore


class RagService:
    def __init__(self) -> None:
        self.vector_store = VectorStore()
        self.llm = LlmService()

    def ask(self, question: str, mode: str, top_k: int | None = None) -> AskResponse:
        k = top_k or settings.top_k
        hits = self.vector_store.search(question=question, mode=mode, top_k=k)
        answer, used_llm = self.llm.answer(question=question, mode=mode, hits=hits)

        citations: List[Citation] = []
        for item, score in hits:
            citations.append(
                Citation(
                    source=item['source'],
                    page=item['page'],
                    domain=item['domain'],
                    score=score,
                    preview=item['text'][:240],
                )
            )

        return AskResponse(answer=answer, mode=mode, citations=citations, used_llm=used_llm)
