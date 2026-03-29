from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


Mode = Literal['DMV', 'MARKET_RESEARCH']


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3)
    mode: Mode
    top_k: Optional[int] = None


class Citation(BaseModel):
    source: str
    page: int
    domain: str
    score: float
    preview: str
    obj_type: str = "text"       # text | table | chart | image
    image_url: Optional[str] = None  # URL to cropped evidence image


class DataPoint(BaseModel):
    label: str
    value: float


class ChartSeries(BaseModel):
    name: str
    data_points: List[DataPoint]


class ChartData(BaseModel):
    title: str
    x_label: str
    y_label: str
    type: str = "line"
    series: List[ChartSeries]


class AskResponse(BaseModel):
    answer: str
    mode: Mode
    citations: List[Citation]
    used_llm: bool
    chart_data: Optional[ChartData] = None


class HealthResponse(BaseModel):
    status: str
    indexed_documents: int
    indexed_chunks: int
