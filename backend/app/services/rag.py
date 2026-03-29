from __future__ import annotations

import json
import re
from typing import Dict, List, Optional, Tuple

from app.config import settings
from app.schemas import AskResponse, ChartData, ChartSeries, Citation, DataPoint
from app.services.llm import LlmService
from app.services.reranker import Reranker
from app.services.vector_store import VectorStore
from app.services.worldbank import build_worldbank_context, detect_indicators

_CHART_BLOCK_RE = re.compile(
    r"```chart\s*\n(\{.*?\})\s*\n```",
    re.DOTALL,
)


def _extract_chart(text: str) -> Tuple[str, Optional[Dict]]:
    """Strip a ```chart {...}``` JSON block from the LLM answer.

    Returns (clean_answer, chart_dict_or_None).
    """
    m = _CHART_BLOCK_RE.search(text)
    if not m:
        return text, None
    try:
        chart_raw = json.loads(m.group(1))
    except (json.JSONDecodeError, ValueError):
        return text, None
    clean = text[: m.start()].rstrip() + text[m.end() :].lstrip()
    return clean.strip(), chart_raw


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
        if mode == "MARKET_RESEARCH":
            indicator_keys = detect_indicators(question)
            if indicator_keys:
                extra_context = build_worldbank_context(indicator_keys)

        # 4. LLM synthesis
        raw_answer, used_llm = self.llm.answer(
            question=question,
            mode=mode,
            hits=reranked,
            extra_context=extra_context,
        )

        # 5. Extract chart JSON block (if LLM decided to include one)
        answer, chart_raw = _extract_chart(raw_answer)

        # 6. Build citations from reranked results
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

        # 7. Build chart data from LLM JSON if present
        chart_data: Optional[ChartData] = None
        if chart_raw and "series" in chart_raw:
            try:
                chart_data = ChartData(
                    title=chart_raw.get("title", "Chart"),
                    x_label=chart_raw.get("x_label", "X"),
                    y_label=chart_raw.get("y_label", "Y"),
                    type=chart_raw.get("type", "line"),
                    series=[
                        ChartSeries(
                            name=s["name"],
                            data_points=[DataPoint(label=str(dp["label"]), value=float(dp["value"])) for dp in s["data_points"]],
                        )
                        for s in chart_raw["series"]
                    ],
                )
            except (KeyError, TypeError, ValueError):
                chart_data = None

        return AskResponse(
            answer=answer,
            mode=mode,
            citations=citations,
            used_llm=used_llm,
            chart_data=chart_data,
        )
