# Voice Navigator - CMPE 277 Hackathon MVP

This monorepo gives you a **working Android + FastAPI RAG starter** for the CMPE 277 hackathon.
It is designed around the professor's brief and wireframes:

<p align="center">
  <video controls width="720" style="max-width:100%;">
    <source src="demo/277_Hackathon_Video.mkv">
    Your browser does not support the video tag. You can download the demo <a href="demo/277_Hackathon_Video.mkv">here</a>.
  </video>
</p>

- **DMV mode** -> answers from the California Driver's Handbook PDF
- **ESG mode** -> answers from the Food Security and Nutrition reports PDFs
- **Voice-first Android UI** -> speech-to-text question input and text-to-speech answer playback
- **RAG backend** -> PDF extraction, chunking, embeddings, vector retrieval, grounded answer generation

## Project structure

```text
voice_navigator_project/
  android/                 # Kotlin + Jetpack Compose Android app
  backend/                 # FastAPI RAG backend
  docs/                    # setup notes and architecture docs
```

## What is already included

- Android app source for a simple voice-driven question/answer app
- Backend ingestion pipeline for PDFs
- RAG retrieval over your uploaded PDFs
- Optional hosted-LLM answer synthesis if you add an API key
- Sample `.env.example`
- The provided PDFs already copied into `backend/data/raw/`

## Quick start

### 1) Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/ingest_documents.py
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2) Android app

Open the `android/` folder in Android Studio.

Then:
1. Let Gradle sync.
2. Use Android emulator or physical device.
3. Make sure backend is running.
4. For emulator, the app points to `http://10.0.2.2:8000/` by default.
5. Grant microphone permission.
6. Ask a DMV or ESG question by typing or speaking.

## How the PDFs are used

The PDFs are the **source of truth** for RAG.

### Ingestion flow

1. Read each PDF from `backend/data/raw/`
2. Extract text with **PyMuPDF**
3. Split text into chunks with overlap
4. Add metadata:
   - source file
   - page number
   - section label
   - domain (`DMV` or `ESG`)
5. Convert chunks to embeddings using `sentence-transformers`
6. Store vectors in **FAISS**
7. Save metadata and original chunk text to disk

### Query flow

1. User asks question in Android app
2. App sends question + selected mode (`DMV` or `ESG`) to backend
3. Backend embeds the question
4. FAISS retrieves top matching chunks from the relevant PDF set
5. Backend builds grounded context from those chunks
6. If API key is configured, hosted LLM rewrites the answer cleanly
7. If no API key is configured, backend returns a grounded extractive answer from retrieved chunks
8. App shows answer and source citations

## Included PDFs

The project already contains copies of these files under `backend/data/raw/`:

- `california_drivers_handbook_2025.pdf`
- `food_security_2023.pdf`
- `food_security_2024.pdf`

## Recommended demo flow

### DMV demo
- "What are blood alcohol concentration limits?"
- "What are signaling signs?"
- "How many attempts do I get for the knowledge test?"

### ESG demo
- "List major food insecurity reasons in 2024"
- "Compare food insecurity reasons in 2023 and 2024"
- "Explain the impact of rising prices on food security"

## Notes

- This is a strong **hackathon MVP** and foundation, not a finished production app.
- The backend will still work without an LLM API key; the answers will just be less polished.
- You can extend this next with quiz mode, bookmarks, search history, charts, and World Bank APIs.
