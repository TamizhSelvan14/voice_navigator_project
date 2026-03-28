from typing import List, Literal, Optional
from pydantic import BaseModel, Field


Mode = Literal['DMV', 'ESG']


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3)
    mode: Mode
    top_k: Optional[int] = None


class Citation(BaseModel):
    source: str
    page: int
    domain: Mode
    score: float
    preview: str


class AskResponse(BaseModel):
    answer: str
    mode: Mode
    citations: List[Citation]
    used_llm: bool


class HealthResponse(BaseModel):
    status: str
    indexed_documents: int
    indexed_chunks: int
