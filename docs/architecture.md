# Architecture

AgentWA is built as a modular self-hosted assistant with three main components:

- **Backend** (`backend/app`): FastAPI service that handles RAG prompt creation, LLM calls, vector retrieval, conversation storage, and the WhatsApp webhook receiver.
- **Frontend** (`frontend`): Next.js app with a chat UI and admin interface for managing documents and viewing gateway status.
- **WhatsApp gateway** (`wa-gateway`): Node.js service using `whatsapp-web.js` to connect to WhatsApp Web, accept incoming messages, and forward them to the backend.

## Message flow

1. WhatsApp message arrives at the gateway.
2. The gateway forwards the message to `POST /whatsapp/webhook` on the backend.
3. The backend records the conversation, optionally retrieves relevant context from ChromaDB, builds a prompt, and calls the configured LLM provider.
4. The backend returns a response payload with `reply`.
5. The gateway sends the reply back to WhatsApp.

## Data storage

- SQLAlchemy stores conversations and document metadata in `data/app.db` by default.
- ChromaDB stores vector indexes in `data/chromadb`.

## LLM providers

- `OLLAMA_URL` / `OLLAMA_MODEL` for local Ollama deployments.
- `GEMINI_URL` / `GEMINI_MODEL` / `GEMINI_API_KEY` for Gemini-compatible services.
