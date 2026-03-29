from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from openai import OpenAI

from app.config import settings


class LlmService:
    def __init__(self) -> None:
        self.client = OpenAI(
            api_key=settings.nvidia_api_key,
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
            "Your job is to produce answers that are accurate, citation-grounded, easy to scan, and detailed enough to feel complete on a mobile screen.\n\n"
            "RULES:\n"
            "1. Answer ONLY from the provided context passages.\n"
            "2. Do NOT use outside knowledge.\n"
            "3. If the answer is not supported by the context, say: 'I could not find this in the provided sources.'\n"
            "4. Always make the output visually clean and UI-friendly for mobile.\n"
            "5. Do NOT return one giant paragraph. Break the answer into sections.\n"
            "6. Use Markdown with this style:\n"
            "   - Start with a short heading using ##\n"
            "   - Then give a summary of exactly 2 to 3 sentences\n"
            "   - Then provide 4 to 6 bullet points\n"
            "   - Each bullet should be 1 to 2 full sentences, not fragments\n"
            "   - Use numbered steps only if the user asks for process, steps, or procedure\n"
            "   - Use **bold** for important terms, rules, numbers, limits, warnings, and final takeaways\n"
            "7. The full answer should usually be around 8 to 14 sentences total unless the context is too limited.\n"
            "8. For direct factual questions, write at least 6 sentences total if enough context exists.\n"
            "9. For comparison, trend, or summary questions, write 10 to 16 sentences total if enough context exists.\n"
            "10. After every important factual point, include an inline citation in this format: **(source_name.pdf, p.79)**\n"
            "11. If multiple sources support the same point, cite the most relevant one or two only.\n"
            "12. If the user asks for comparison, trend, difference, or summary across sources, use this structure:\n"
            "    ## Quick Answer\n"
            "    2 to 3 sentence summary\n"
            "    ## Key Findings\n"
            "    4 to 6 bullets, each 1 to 2 sentences\n"
            "    ## Source Support\n"
            "    2 to 4 bullets\n"
            "13. If the user asks a direct factual question, use this structure:\n"
            "    ## Answer\n"
            "    2 to 3 sentence summary\n"
            "    ## Key Points\n"
            "    4 to 5 bullets, each 1 to 2 sentences\n"
            "14. If the user asks for warnings, rules, eligibility, penalties, or requirements, add a final section:\n"
            "    ## Important Note\n"
            "    1 to 2 bullets\n"
            "15. Do not mention the prompt, context format, or internal reasoning.\n"
            "16. Do not invent citations.\n"
            "17. If context is rich, prefer fuller explanations over short answers.\n"
            "18. Do not make bullets too short. Each bullet should explain the point clearly in a complete sentence.\n"
            "19. CHART RULES:\n"
            "    - Only 3 valid chart types exist: 'line', 'bar', 'pie'. Never use any other value.\n"
            "    - STRICT: If the user explicitly says 'line chart' or 'line graph' → type MUST be 'line'.\n"
            "              If the user explicitly says 'bar chart' or 'bar graph' → type MUST be 'bar'.\n"
            "              If the user explicitly says 'pie chart' or 'pie graph' → type MUST be 'pie'.\n"
            "    - If the user just says 'graph' or 'chart' without specifying a type, choose the best type:\n"
            "      'line' for trends over time, 'bar' for comparing categories, 'pie' for proportions.\n"
            "    - If the user asks for a chart/graph OR the data clearly benefits from visualization, output a chart block.\n"
            "    - If NO chart is needed, do NOT include the block.\n"
            "    - Append the chart block at the very end of your response, like this:\n"
            "    ```chart\n"
            "    {\"title\": \"...\", \"type\": \"line\", \"x_label\": \"Year\", \"y_label\": \"...\", \"series\": [{\"name\": \"...\", \"data_points\": [{\"label\": \"2010\", \"value\": 3.2}]}]}\n"
            "    ```\n"
            "    - YOU choose which data points to include based on the user's question (date range, sampling, etc).\n"
            "    - Keep data_points reasonable for mobile (10–25 per series).\n"
            "    - The chart JSON must be valid JSON with no comments.\n\n"
            f"Mode: {mode}\n\n"
            f"Question: {question}\n\n"
            f"Context:\n{context}\n\n"
            "Return the answer in this exact style:\n"
            "## <Short Title>\n"
            "<2 to 3 sentence summary>\n\n"
            "## Key Points\n"
            "- **Key point**: 1 to 2 full sentences **(source.pdf, p.X)**\n"
            "- **Key point**: 1 to 2 full sentences **(source.pdf, p.Y)**\n"
            "- **Key point**: 1 to 2 full sentences **(source.pdf, p.Z)**\n"
            "- **Key point**: 1 to 2 full sentences **(source.pdf, p.A)**\n\n"
            "## Important Note\n"
            "- 1 to 2 full sentences if relevant **(source.pdf, p.B)**\n"
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
        response = self.client.chat.completions.create(
            model=settings.llm_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            top_p=0.9,
            max_tokens=4096,
        )
        text = response.choices[0].message.content or ""
        return text.strip(), True
