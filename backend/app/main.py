from pathlib import Path
import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.schemas import AskRequest, AskResponse, HealthResponse
from app.services.rag import RagService

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)

# Serve cropped evidence images
assets_dir = settings.assets_dir
assets_dir.mkdir(parents=True, exist_ok=True)
app.mount('/assets', StaticFiles(directory=str(assets_dir)), name='assets')

rag_service = RagService()


def _index_counts() -> tuple[int, int]:
    metadata_path = settings.processed_data_dir / 'metadata.json'
    if not metadata_path.exists():
        return 0, 0
    items = json.loads(metadata_path.read_text(encoding='utf-8'))
    docs = len({item['source'] for item in items})
    return docs, len(items)


@app.get('/health', response_model=HealthResponse)
def health() -> HealthResponse:
    docs, chunks = _index_counts()
    return HealthResponse(status='ok', indexed_documents=docs, indexed_chunks=chunks)


@app.post('/ask', response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    try:
        return rag_service.ask(question=request.question, mode=request.mode, top_k=request.top_k)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc))
