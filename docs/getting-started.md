# Getting Started

## Prerequisites

- Docker & Docker Compose
- Node.js 18+ for local frontend and gateway development
- Python 3.12 or 3.13 for the backend

## Local backend setup

```bash
cd backend
python -m venv .venv
. .venv/Scripts/Activate.ps1  # Windows PowerShell
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Local frontend setup

```bash
cd frontend
npm install
npm run dev
```

## WhatsApp gateway

```bash
cd wa-gateway
npm install
node server.js
```

## Docker Compose quickstart

```bash
docker compose up -d --build
```

## Viewing the app

- Frontend: http://localhost:3000
- Backend OpenAPI: http://localhost:8000/docs
- WhatsApp QR/status: http://localhost:3001/qr and http://localhost:3001/status

## RAG commands and knowledge updates

The backend supports command-based knowledge updates from chat or WhatsApp messages.

Supported commands:
- `/help` — show available commands.
- `/addtext <text>` — add inline text to the knowledge base and index it.
- `/addurl <url>` — download and extract text from the specified URL, then index it.
- `/reindex` — refresh all document embeddings in the ChromaDB vector store.
- `/stats` — return counts for documents, URLs, chats, and stored vector rows.
- `/apis` — list API entries configured in the backend.
- `/runapi <name|id>` — execute a configured API entry and return the response payload.

How RAG is updated:
- `/addtext` and `/addurl` create new documents in the app database and immediately add document chunks to ChromaDB.
- `chunk_text` splits long content into overlapping chunks before embedding.
- `/reindex` deletes existing vectors for all documents and re-adds them to keep the index consistent.
- Non-command messages use the current vector store to retrieve relevant context, then call the LLM with that context.

Useful environment variables for RAG behavior:
- `CHROMA_DIR` — directory for ChromaDB persistence.
- `CHUNK_SIZE` — number of words per chunk when splitting documents.
- `RETRIEVAL_COUNT` — number of nearest-neighbor results used to build prompts.
