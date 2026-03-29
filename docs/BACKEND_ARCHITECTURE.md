# Backend Architecture — Voice Navigator

## Overview

The backend is a **FastAPI RAG (Retrieval-Augmented Generation) pipeline** that answers questions grounded in PDF documents. It runs two modes:

- **DMV** — California Driver's Handbook 2025
- **ESG** — Food Security and Nutrition reports (2023 and 2024)

---

## Tech Stack

| Layer           | Library / Tool                 | Version       |
| --------------- | ------------------------------ | ------------- |
| Web framework   | FastAPI                        | 0.115.0       |
| ASGI server     | Uvicorn (with standard extras) | 0.30.6        |
| Data validation | Pydantic + pydantic-settings   | 2.9.2 / 2.5.2 |
| PDF extraction  | PyMuPDF (`fitz`)               | ≥ 1.24.10     |
| Embedding model | sentence-transformers          | 3.1.1         |
| Vector index    | FAISS (CPU)                    | 1.9.0.post1   |
| Numeric ops     | NumPy                          | 1.26.4        |
| LLM (optional)  | OpenAI Python SDK              | 1.47.0        |
| Env config      | python-dotenv                  | 1.0.1         |

---

## Folder Structure

```
backend/
  app/
    config.py          ← all settings loaded from .env
    main.py            ← FastAPI app, routes: /health, /ask
    schemas.py         ← Pydantic request/response models
    services/
      pdf_ingest.py    ← PDF extraction + chunking
      vector_store.py  ← embedding + FAISS index build/search
      rag.py           ← orchestrates retrieve → answer → citations
      llm.py           ← LLM synthesis (OpenAI) or extractive fallback
  data/
    raw/               ← original PDF files (3 PDFs)
    processed/
      chunks.jsonl     ← all chunk records (text + metadata)
      metadata.json    ← same data as array (used by vector store)
      vector.index     ← FAISS binary index file
  scripts/
    ingest_documents.py ← one-time ingestion script
```

---

## Step 1 — PDF Extraction

**File**: `app/services/pdf_ingest.py`  
**Library**: `PyMuPDF` (`import fitz`)

### What it does

- Opens each `.pdf` from `data/raw/` using `fitz.open()`
- Iterates page by page with `page.get_text('text')` to extract raw text
- Cleans the text:
  - Replaces non-breaking spaces (`\u00a0`) with regular spaces
  - Collapses all whitespace sequences (`\s+`) into a single space
- Skips pages that produce empty text after cleaning

### Domain inference

The domain tag (`DMV` or `ESG`) is assigned by checking the PDF filename:

```python
if 'driver' in name or 'dmv' in name or 'handbook' in name:
    return 'DMV'
return 'ESG'
```

### Section label

A rough section label is extracted from the first 80 characters of the page text (before the first `.`). This is stored in metadata for citation display.

---

## Step 2 — Chunking

**File**: `app/services/pdf_ingest.py` — `PdfIngester.chunk_text()`

### Strategy: Fixed-size sliding window with overlap

| Parameter    | Value              |
| ------------ | ------------------ |
| `chunk_size` | **900 characters** |
| `overlap`    | **150 characters** |

### How it works

```
[  chunk 1: chars 0–900   ]
               [  chunk 2: chars 750–1650  ]
                              [  chunk 3: chars 1500–2400  ]
```

- Each chunk overlaps with the previous by 150 characters
- This prevents context from being cut at a hard boundary — relevant sentences that fall at the edge of a chunk still appear in the next chunk
- Chunks are character-based (not token-based)

### Chunk record structure

Each chunk is stored as a `ChunkRecord` dataclass:

```python
@dataclass
class ChunkRecord:
    chunk_id: str    # e.g. "california_drivers_handbook_2025-p12-c3"
    domain:   str    # "DMV" or "ESG"
    source:   str    # filename e.g. "california_drivers_handbook_2025.pdf"
    page:     int    # 1-based page number
    section:  str    # rough section label from page start
    text:     str    # the chunk text
```

### Current ingestion results

- **3 PDFs** processed
- **3,142 total chunks** produced
- Saved to `data/processed/chunks.jsonl` (one JSON object per line)

---

## Step 3 — Embedding

**File**: `app/services/vector_store.py`  
**Model**: `sentence-transformers/all-MiniLM-L6-v2`

### Model details

| Property            | Value                                              |
| ------------------- | -------------------------------------------------- |
| Model name          | `sentence-transformers/all-MiniLM-L6-v2`           |
| Architecture        | MiniLM (distilled BERT, 6 layers)                  |
| Output dimensions   | **384**                                            |
| Max sequence length | 256 tokens                                         |
| Training task       | Semantic textual similarity (STS)                  |
| Size                | ~90 MB                                             |
| Device              | **CPU** (forced — avoids MPS crashes on macOS ARM) |

### Encoding settings

```python
self.model.encode(
    texts,
    normalize_embeddings=True,   # L2-normalizes output vectors → enables cosine similarity via dot product
    show_progress_bar=True,
    batch_size=8,
    device="cpu",
    convert_to_numpy=True,
)
```

`normalize_embeddings=True` is important — it means dot product (`IndexFlatIP`) behaves as **cosine similarity**.

### Output

A `float32` NumPy matrix of shape `(3142, 384)` — one 384-dim vector per chunk.

---

## Step 4 — Vector Index (FAISS)

**File**: `app/services/vector_store.py`  
**Library**: `faiss-cpu`

### Index type: `IndexFlatIP`

| Property          | Detail                                                                |
| ----------------- | --------------------------------------------------------------------- |
| Index type        | `IndexFlatIP` (Flat Inner Product)                                    |
| Search method     | Exact / brute-force nearest-neighbor                                  |
| Similarity metric | Inner product = cosine similarity (because vectors are L2-normalized) |
| Dimensions        | 384                                                                   |
| Stored vectors    | 3,142                                                                 |

`IndexFlatIP` does **no compression or approximation** — it compares the query against every vector exactly. This is fine for 3,142 vectors (sub-millisecond search).

### Index files saved to disk

```
data/processed/vector.index    ← FAISS binary index (faiss.write_index)
data/processed/metadata.json   ← parallel array of chunk metadata
```

The index and metadata are loaded once on first query (`ensure_loaded()`) and kept in memory for subsequent requests.

---

## Step 5 — Retrieval (RAG Query Flow)

**File**: `app/services/vector_store.py` — `VectorStore.search()`

### Query pipeline

1. Encode the user's question using the **same embedding model** (`all-MiniLM-L6-v2`)
2. Search FAISS with `search_k = min(len(metadata), max(top_k * 100, 500))` — pulls a large candidate pool first
3. **Domain filter**: iterate results and only keep chunks where `item["domain"] == mode` (DMV or ESG)
4. Return the top `k` domain-matched results as `(metadata_dict, score)` tuples

Default `top_k = 4` (set in `config.py`).

The two-step approach (large FAISS pool → domain filter) is used because `IndexFlatIP` doesn't support filtered search natively. Pulling 500 candidates and then filtering guarantees finding at least `top_k` domain-specific hits.

---

## Step 6 — Answer Generation

**File**: `app/services/llm.py`

### Two modes depending on whether an OpenAI API key is configured:

#### Mode A — Extractive fallback (no API key, current state)

```
OPENAI_API_KEY= (empty in .env)
→ self.enabled = False
```

- Takes the top 3 retrieved chunks
- Truncates each to 320 characters
- Returns them as bullet points prefixed with `"Grounded answer from retrieved PDF passages:"`
- `used_llm: false` in response

#### Mode B — LLM synthesis (with API key)

```
OPENAI_API_KEY=sk-...
→ self.enabled = True
```

- Builds a prompt with all `top_k` retrieved chunks as context, including source/page/score metadata
- Calls **OpenAI `gpt-4o-mini`** via `client.responses.create()`
- Temperature `0.2` (low, for factual answers)
- System instruction: answer only from context, say if not found, keep it concise for mobile
- `used_llm: true` in response

### Prompt structure (Mode B)

```
You are a grounded assistant for a voice-first mobile app.
Answer the user only from the provided context.
If the answer is not in context, say that clearly.
Mode: DMV.

Question: <user question>

Context:
[Source: california_drivers_handbook_2025.pdf | Page: 79 | Score: 0.630]
<chunk text>

[Source: ... ]
<chunk text>

Return a concise, clear answer suitable for a mobile screen.
```

---

## API Endpoints

**File**: `app/main.py`

### `GET /health`

Returns index status.

```json
{
  "status": "ok",
  "indexed_documents": 3,
  "indexed_chunks": 3142
}
```

### `POST /ask`

Request:

```json
{
  "question": "What are blood alcohol concentration limits?",
  "mode": "DMV",
  "top_k": 4
}
```

Response:

```json
{
  "answer": "...",
  "mode": "DMV",
  "used_llm": false,
  "citations": [
    {
      "source": "california_drivers_handbook_2025.pdf",
      "page": 79,
      "domain": "DMV",
      "score": 0.6298,
      "preview": "73 Blood Alcohol Concentration (BAC) Limits..."
    }
  ]
}
```

CORS is set to `allow_origins=['*']` — accepts requests from any origin (needed for emulator → host communication).

---

## Configuration (`.env`)

| Key               | Default                                  | Purpose                                                           |
| ----------------- | ---------------------------------------- | ----------------------------------------------------------------- |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | HuggingFace model ID for embeddings                               |
| `TOP_K`           | `4`                                      | Number of chunks to retrieve per query                            |
| `OPENAI_API_KEY`  | _(empty)_                                | If set, enables GPT synthesis. If empty, uses extractive fallback |
| `OPENAI_MODEL`    | `gpt-4o-mini`                            | Which OpenAI model to call                                        |
| `HOST`            | `0.0.0.0`                                | Bind address                                                      |
| `PORT`            | `8000`                                   | Bind port                                                         |

---

## Full Data Flow Summary

```
PDF files (data/raw/)
        │
        ▼
[PyMuPDF] page-by-page text extraction
        │
        ▼
[PdfIngester] clean text → sliding window chunks (900 chars, 150 overlap)
        │  produces ChunkRecord: chunk_id, domain, source, page, section, text
        ▼
[VectorStore.build()] encode all chunk texts
        │  model: all-MiniLM-L6-v2 → 384-dim L2-normalized float32 vectors
        ▼
[FAISS IndexFlatIP] store all vectors + write index to disk
        │  vector.index + metadata.json saved to data/processed/
        ▼
════════════════════════════ (ingestion done, one-time) ════════════════════════

User question → POST /ask  { question, mode, top_k }
        │
        ▼
[VectorStore.search()] embed question → FAISS search 500 candidates → domain filter → top 4
        │  returns List[(chunk_metadata, cosine_score)]
        ▼
[LlmService.answer()]
   if no API key → extractive bullet answer from top 3 chunks
   if API key    → GPT-4o-mini synthesizes clean answer from all 4 chunks
        │
        ▼
[RagService] builds AskResponse with answer + citations (source, page, score, preview)
        │
        ▼
JSON response → Android app
```

---

## What Is Complete

| Component                                        | Status           |
| ------------------------------------------------ | ---------------- |
| PDF extraction (PyMuPDF page text)               | Done             |
| Text cleaning (whitespace, NBSP)                 | Done             |
| Chunking (900 char / 150 overlap sliding window) | Done             |
| Domain tagging (DMV / ESG by filename)           | Done             |
| Embedding (all-MiniLM-L6-v2, 384-dim, CPU)       | Done             |
| FAISS index build + persist to disk              | Done             |
| FAISS search with domain filtering               | Done             |
| Extractive fallback answer (no API key)          | Done             |
| LLM synthesis via GPT-4o-mini (with API key)     | Coded, needs key |
| Citations with source, page, score, preview      | Done             |
| FastAPI `/health` and `/ask` endpoints           | Done             |
| CORS for emulator/browser access                 | Done             |
| Config via `.env` / pydantic-settings            | Done             |

## What Is Not Yet Done

| Feature                  | Notes                                                                                                                    |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------ |
| OpenAI API key           | Add `OPENAI_API_KEY=sk-...` to `.env` to activate LLM mode                                                               |
| Streaming responses      | Currently returns full answer at once; could use SSE for TTS-friendliness                                                |
| Quiz mode endpoint       | New `/quiz` endpoint not implemented                                                                                     |
| User history / bookmarks | No database, no persistence of Q&A sessions                                                                              |
| Token-based chunking     | Current chunking is character-based; switching to token-based (e.g. tiktoken) would respect model context windows better |
| Re-ranking               | No cross-encoder re-ranking step after FAISS retrieval                                                                   |
| Caching                  | No answer caching for repeated questions                                                                                 |
