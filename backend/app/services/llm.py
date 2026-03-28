from __future__ import annotations

from typing import Dict, List, Tuple

from app.config import settings

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None


class LlmService:
    def __init__(self) -> None:
        self.enabled = bool(settings.openai_api_key and OpenAI is not None)
        self.client = OpenAI(api_key=settings.openai_api_key) if self.enabled else None

    def build_prompt(self, question: str, mode: str, hits: List[Tuple[Dict, float]]) -> str:
        context_blocks = []
        for item, score in hits:
            context_blocks.append(
                f"[Source: {item['source']} | Page: {item['page']} | Score: {score:.3f}]\n{item['text']}"
            )
        context = "\n\n".join(context_blocks)
        return (
            "You are a grounded assistant for a voice-first mobile app. "
            "Answer the user only from the provided context. "
            "If the answer is not in context, say that clearly. "
            f"Mode: {mode}.\n\n"
            f"Question: {question}\n\n"
            f"Context:\n{context}\n\n"
            "Return a concise, clear answer suitable for a mobile screen."
        )

    def answer(self, question: str, mode: str, hits: List[Tuple[Dict, float]]) -> tuple[str, bool]:
        if not hits:
            return "I could not find supporting text in the indexed PDFs for that question.", False

        if not self.enabled:
            bullets = []
            for item, _score in hits[:3]:
                bullets.append(f"- {item['text'][:320].strip()}...")
            answer = "Grounded answer from retrieved PDF passages:\n" + "\n".join(bullets)
            return answer, False

        prompt = self.build_prompt(question, mode, hits)
        response = self.client.responses.create(
            model=settings.openai_model,
            input=prompt,
            temperature=0.2,
        )
        return response.output_text.strip(), True
