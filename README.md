AgentWA — Self-hosted Agentic RAG with WhatsApp QR gateway
=========================================================

This repository contains a lightweight RAG assistant (FastAPI backend, ChromaDB vectors, Gemini/Ollama LLM) and a self-hosted WhatsApp gateway (wa-gateway) that uses WhatsApp Web (no third-party services). The frontend is a simple Next.js app with a WhatsApp-style chat UI and admin panel.

Quick overview
- Backend: `backend/app` (FastAPI)
- Frontend: `frontend` (Next.js + Tailwind)
- WhatsApp gateway: `wa-gateway` (Node + whatsapp-web.js)
- Vector store: ChromaDB (persisted under `data/chromadb`)
- Orchestration: `docker-compose.yml`
- Docs: `mkdocs.yml` + `docs/`

Documentation
- Local docs server: `python -m pip install -r requirements-docs.txt && mkdocs serve`
- GitHub Pages deploy: `.github/workflows/gh-pages.yml`

Prerequisites
- Docker & Docker Compose
- Node.js (for local frontend / gateway dev)
- Python 3.12 or 3.13 recommended for local backend dev (Windows users: avoid Python 3.14 due to native build issues)

Quickstart (recommended: Docker Compose)
1. Copy environment template and edit required keys:

```bash
cp .env.example .env
# On Windows PowerShell:
# Copy-Item .env.example .env
```

2. Fill in any secrets in `.env` (e.g. `GEMINI_API_KEY` or `GEMINI_*` settings if using Gemini).

3. Start the stack with Docker Compose:

```bash
docker compose up -d --build
```

4. Visit the apps:
- Frontend (chat + admin): http://localhost:3000
- Backend OpenAPI: http://localhost:8000/docs
- WhatsApp gateway QR/status: http://localhost:3001/qr  and http://localhost:3001/status

RAG commands and knowledge update
- The backend supports chat and WhatsApp commands that update the vector store and knowledge base.
- Commands are parsed from incoming chat or WhatsApp text before normal retrieval.
- Supported commands:
  - `/help` — list available commands.
  - `/addtext <text>` — add raw text as a new knowledge document and create embeddings immediately.
  - `/addurl <url>` — fetch the URL content, save it as a document, and add it to ChromaDB.
  - `/reindex` — rebuild vectors for all stored documents, refreshing the vector store.
  - `/stats` — return counts for documents, URLs, chat conversations, and stored vectors.
  - `/apis` — list stored API entries configured in the backend.
  - `/runapi <name|id>` — execute a configured API entry and return the response.

How it works
- Incoming chat or WhatsApp messages are stored in the database.
- If a command is detected, the backend handles it directly and returns a command response.
- Otherwise, the message is used to query ChromaDB and retrieve the top relevant document chunks.
- Retrieved context is included in a generated prompt and sent to the configured LLM provider (`ollama` or `gemini`).
- The LLM response is then saved and returned to the user.

Local development (optional)

Backend (Windows PowerShell example):

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:3000
```

WhatsApp gateway (local, requires Node and dependencies):

```bash
cd wa-gateway
npm install
node server.js
# Open http://localhost:3001/qr to fetch QR DataURL
```

How to connect WhatsApp (QR flow)
1. Start `wa-gateway` (or use the Docker Compose service).  The gateway will generate a QR code.
2. Open the Admin page → WhatsApp Gateway, click "Refresh QR" (or visit `/qr`).
3. On your phone: WhatsApp → Settings → Linked devices → Link a device → scan the QR shown.
4. Once connected the gateway will remain linked via LocalAuth session (session files stored in `wa-gateway/session`). Incoming messages will be forwarded to your backend `/whatsapp/webhook` and replies will be sent back through the gateway.

Environment variables (key ones)
- `DATABASE_URL` — e.g. `sqlite:///./data/app.db`
- `CHROMA_DIR` — where ChromaDB stores vectors
- `LLM_PROVIDER` — `ollama` or `gemini`
- `GEMINI_API_KEY` — your Gemini/OpenAI-compatible API key (if using Gemini)
- `GEMINI_URL`, `GEMINI_MODEL` — override Gemini endpoint/model
- `OLLAMA_URL`, `OLLAMA_MODEL` — if using Ollama
- `CHUNK_SIZE`, `RETRIEVAL_COUNT` — RAG tuning
- `BACKEND_URL` (wa-gateway env) — where the gateway forwards incoming messages (default used in compose)

Why Python 3.12/3.13?
Some packages (notably `pydantic-core`) may require Rust toolchain or prebuilt wheels. On Windows, using Python 3.12/3.13 will use available wheels and avoid building from source.

Troubleshooting
- If `pip install` fails building `pydantic-core`, switch to Python 3.12/3.13 or install Rust/Cargo toolchains (not recommended for quick setup).
- If the gateway cannot connect or QR never clears: remove `wa-gateway/session` and restart to force new session.
- Gateway Puppeteer notes: the Dockerfile includes apt deps for headless Chromium; if running locally you may need to install system packages for Puppeteer.

Security and production notes
- This gateway exposes endpoints that should be secured when public. Add HTTPS / TLS and restrict access via firewall or API keys.
- For production, consider adding a shared secret between `wa-gateway` and the backend, and require it on the `/whatsapp/webhook` forward.

Next steps you might want me to do
- Add a backend `POST /whatsapp/send` endpoint to let the assistant push proactive messages through the gateway.
- Add an API key between gateway and backend for authentication.
- Support media (images, attachments) and better error reporting.

If you'd like, I can now:
- implement the secure backend outbound endpoint to drive `wa-gateway` (assistant-initiated messages), or
- add the shared-secret authentication for gateway↔backend communication.

--
Generated README for `AgentWA` by assistant.