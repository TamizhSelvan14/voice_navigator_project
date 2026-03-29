from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from app.config import settings
from app.schemas import AskResponse, ChartData, ChartSeries, Citation, DataPoint
from app.services.llm import LlmService
from app.services.reranker import Reranker
from app.services.vector_store import VectorStore
from app.services.worldbank import build_worldbank_context, detect_indicators


class RagService:
    def __init__(self) -> None:
        self.vector_store = VectorStore()
        self.reranker = Reranker()
        self.llm = LlmService()

    def ask(self, question: str, mode: str, top_k: int | None = None) -> AskResponse:
        k = top_k or settings.top_k

        # 1. Initial retrieval — fetch more candidates for reranking
        domain = "ESG" if mode == "MARKET_RESEARCH" else mode
        hits = self.vector_store.search(question=question, mode=domain, top_k=k)

        # 2. Rerank for precision
        reranked = self.reranker.rerank(query=question, hits=hits, top_k=settings.rerank_top_k)

        # 3. World Bank data (only for MARKET_RESEARCH)
        extra_context = ""
        chart_data_raw: Optional[Dict] = None
        if mode == "MARKET_RESEARCH":
            indicator_keys = detect_indicators(question)
            if indicator_keys:
                extra_context, chart_data_raw = build_worldbank_context(indicator_keys)

        # 4. LLM synthesis
        answer, used_llm = self.llm.answer(
            question=question,
            mode=mode,
            hits=reranked,
            extra_context=extra_context,
        )

        # 5. Build citations from reranked results
        citations: List[Citation] = []
        for item, score in reranked:
            citations.append(
                Citation(
                    source=item["source"],
                    page=item["page"],
                    domain=item["domain"],
                    score=score,
                    preview=item["text"][:240],
                )
            )

        # 6. Parse chart data if present
        chart_data: Optional[ChartData] = None
        if chart_data_raw:
            chart_data = ChartData(
                title=chart_data_raw["title"],
                x_label=chart_data_raw["x_label"],
                y_label=chart_data_raw["y_label"],
                type=chart_data_raw.get("type", "line"),
                series=[
                    ChartSeries(
                        name=s["name"],
                        data_points=[DataPoint(**dp) for dp in s["data_points"]],
                    )
                    for s in chart_data_raw["series"]
                ],
            )

        return AskResponse(
            answer=answer,
            mode=mode,
            citations=citations,
            used_llm=used_llm,
            chart_data=chart_data,
        )
