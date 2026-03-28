# Step-by-step setup

## Backend

1. Open terminal
2. Go to backend folder
3. Create virtual environment
4. Install requirements
5. Copy `.env.example` to `.env`
6. Add your API key only if you want hosted LLM rewriting
7. Run ingestion script
8. Start FastAPI server
9. Open `http://localhost:8000/docs`

Commands:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/ingest_documents.py
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Android

1. Open Android Studio
2. Choose **Open**
3. Select the `android/` folder
4. Wait for Gradle sync
5. Run on emulator
6. Accept microphone permission
7. Ask questions in DMV or ESG mode

## Emulator networking

- Android emulator -> use `http://10.0.2.2:8000/`
- Physical device -> replace the base URL with your computer's LAN IP

## First end-to-end test

1. Start backend
2. Open app
3. Select **DMV** mode
4. Ask: `What are blood alcohol concentration limits?`
5. Confirm answer and source pages appear
6. Switch to **ESG**
7. Ask: `List major food insecurity reasons in 2024`

## Next improvements

1. Add quiz mode for DMV
2. Add bookmarks/history with Room
3. Add World Bank chart APIs for GDP/CO2/agri land
4. Add login and cloud sync
5. Add caching and offline answer history
