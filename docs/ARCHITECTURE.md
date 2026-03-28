# Architecture

## Why this architecture fits the hackathon

The assignment expects a **voice-first mobile app** backed by **document-grounded retrieval**.
So the clean MVP architecture is:

```text
Android app (Kotlin + Compose)
    -> REST call
FastAPI backend
    -> Command routing
    -> RAG retrieval over PDFs
    -> Optional LLM synthesis
    -> Response with citations
```

## Components

### Android app
- Jetpack Compose UI
- Voice input through Android speech recognizer
- Text-to-speech playback
- Retrofit network client
- MVVM state management

### Backend
- FastAPI
- PDF ingestion with PyMuPDF
- Embeddings with sentence-transformers
- FAISS vector search
- Optional OpenAI answer synthesis

## PDF handling

The PDFs are stored locally in `backend/data/raw/`.
They are preprocessed once using the ingestion script and turned into:

- `chunks.jsonl`
- `metadata.json`
- `vector.index`

These files are stored in `backend/data/processed/`.

## Why we use FAISS instead of a normal SQL DB for retrieval

A normal relational database is good for:
- user history
- bookmarks
- quiz scores
- app settings

But semantic retrieval from long documents is better with:
- embeddings
- nearest-neighbor search
- vector index

That is why the PDF knowledge base uses **FAISS**.
