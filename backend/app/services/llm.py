from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from openai import OpenAI

from app.config import settings


class LlmService:
    def __init__(self) -> None:
        self.client = OpenAI(
            api_key=settings.next_api_key(),
            base_url=settings.nvidia_base_url,
        )

    def build_prompt(
        self,
        question: str,
        mode: str,
        hits: List[Tuple[Dict, float]],
        extra_context: str = "",
    ) -> str:
        context_blocks: List[str] = []
        for item, score in hits:
            context_blocks.append(
                f"[Source: {item['source']} | Page: {item['page']} | Score: {score:.3f}]\n{item['text']}"
            )
        if extra_context:
            context_blocks.append(f"[Source: World Bank API]\n{extra_context}")
        context = "\n\n".join(context_blocks)
        return (
            "You are a highly knowledgeable, grounded assistant for a voice-first mobile app.\n"
            "Your job is to produce answers that are accurate, citation-grounded, and very easy to scan on a mobile screen.\n\n"
            "RULES:\n"
            "1. Answer ONLY from the provided context passages.\n"
            "2. Do NOT use outside knowledge.\n"
            "3. If the answer is not supported by the context, say: 'I could not find this in the provided sources.'\n"
            "4. Always make the output visually clean and UI-friendly for mobile.\n"
            "5. Do NOT return one large paragraph unless the answer is extremely short.\n"
            "6. Use Markdown with this style:\n"
            "   - Start with a short heading using ##\n"
            "   - Then give a 1 to 2 line summary\n"
            "   - Then use bullets for key points\n"
            "   - Use numbered steps only if the user asks for process, steps, or procedure\n"
            "   - Use **bold** for important terms, rules, numbers, limits, warnings, and final takeaways\n"
            "7. Keep answers concise but useful. Prefer short sections over dense text.\n"
            "8. After every important factual point, include an inline citation in this format: **(source_name.pdf, p.79)**\n"
            "9. If multiple sources support the same point, cite the most relevant one or two only.\n"
            "10. If the user asks for comparison, trend, difference, or summary across sources, use this structure:\n"
            "    ## Quick Answer\n"
            "    ## Key Findings\n"
            "    ## Source Support\n"
            "11. If the user asks a direct factual question, use this structure:\n"
            "    ## Answer\n"
            "    - Key point 1\n"
            "    - Key point 2\n"
            "    - Key point 3\n"
            "12. If the user asks for warnings, rules, eligibility, penalties, or requirements, add a final section:\n"
            "    ## Important Note\n"
            "13. Do not mention the prompt, context format, or internal reasoning.\n"
            "14. Do not invent citations.\n\n"
            f"Mode: {mode}\n\n"
            f"Question: {question}\n\n"
            f"Context:\n{context}\n\n"
            "Return the answer in this exact style:\n"
            "## <Short Title>\n"
            "<1 to 2 line summary>\n\n"
            "- **Key point**: explanation **(source.pdf, p.X)**\n"
            "- **Key point**: explanation **(source.pdf, p.Y)**\n\n"
            "## Important Note\n"
            "- short warning / rule / takeaway if relevant **(source.pdf, p.Z)**\n"
        )

    def answer(
        self,
        question: str,
        mode: str,
        hits: List[Tuple[Dict, float]],
        extra_context: str = "",
    ) -> Tuple[str, bool]:
        if not hits and not extra_context:
            return "I could not find supporting text in the indexed documents for that question.", False

        prompt = self.build_prompt(question, mode, hits, extra_context)
        self.client.api_key = settings.next_api_key()
        response = self.client.chat.completions.create(
            model="moonshotai/kimi-k2-instruct-0905",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            top_p=0.9,
            max_tokens=4096,
            # extra_body={"chat_template_kwargs":{"enable_thinking":False}},
        )
        text = response.choices[0].message.content or ""
        return text.strip(), True
