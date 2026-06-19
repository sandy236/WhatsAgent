import json
import logging
import tempfile
from typing import Optional, List
from xml.sax.saxutils import escape

import requests
from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException, BackgroundTasks, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .config import CORS_ORIGINS, CHUNK_SIZE, RETRIEVAL_COUNT
from .db import Base, engine, SessionLocal
from .embeddings import add_document_vectors, query_vectors, delete_document_vectors, count_vectors
from .models import Document, Conversation, Message, ApiEntry, Setting
from .ollama_client import ask_llm, stream_llm
from .schemas import ChatRequest, ChatResponse, DocumentRecord, ApiEntrySchema, SettingSchema, StatsResponse
from .utils import (
    clean_text,
    chunk_text,
    extract_text_from_file,
    fetch_url_text,
    save_upload_temp,
)

logger = logging.getLogger("agent")
app = FastAPI(title="Agentic RAG Assistant")
origins = [origin.strip() for origin in CORS_ORIGINS.split(",") if origin.strip()]
if not origins:
    origins = ["*"]
# If wildcard origins are used, credentials cannot be allowed per CORS spec.
allow_credentials = True
if origins == ["*"]:
    allow_credentials = False
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_or_create_conversation(db: Session, conversation_id: Optional[int] = None) -> Conversation:
    if conversation_id:
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if conversation:
            return conversation
    conversation = Conversation(name="Agent Chat")
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def record_message(db: Session, conversation: Conversation, role: str, content: str) -> Message:
    message = Message(conversation_id=conversation.id, role=role, content=content)
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_or_create_whatsapp_conversation(db: Session, from_number: str) -> Conversation:
    name = f"whatsapp:{from_number}"
    conversation = db.query(Conversation).filter(Conversation.name == name).first()
    if conversation:
        return conversation
    conversation = Conversation(name=name)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@app.post("/whatsapp/webhook")
def whatsapp_webhook(
    request: Request,
    From: str = Form(...),
    Body: str = Form(...),
    db: Session = Depends(get_db),
):
    sender = From
    incoming_text = Body.strip()
    logger.info('WhatsApp webhook received message from %s: %s', sender, incoming_text)
    logger.debug('WhatsApp webhook headers=%s', dict(request.headers))
    conversation = get_or_create_whatsapp_conversation(db, sender)
    record_message(db, conversation, "user", incoming_text)

    command = parse_command(incoming_text, db)
    logger.info('Parsed command=%s', command)
    if command:
        response_text = command_response(command, db)
    else:
        logger.info('Running vector retrieval for incoming text')
        results = query_vectors(incoming_text, limit=RETRIEVAL_COUNT)
        prompt = build_prompt_with_context(incoming_text, results)
        logger.debug('Built prompt length=%s', len(prompt))
        try:
            response_text = ask_llm(prompt)
        except Exception as exc:
            logger.exception('LLM call failed while handling WhatsApp webhook')
            response_text = 'Sorry, I could not generate a response right now. Please try again later.'

    if not response_text or not response_text.strip():
        logger.error('LLM returned empty reply for WhatsApp webhook; using fallback text')
        response_text = 'Sorry, I could not generate a response right now. Please try again later.'

    record_message(db, conversation, "assistant", response_text)
    logger.info('WhatsApp webhook responding to %s with: %s', sender, response_text)

    if request.headers.get("x-whatsapp-gateway") == "1" or "application/json" in request.headers.get("accept", ""):
        return {"reply": response_text}

    twiml = f"<Response><Message>{escape(response_text)}</Message></Response>"
    return Response(content=twiml, media_type="application/xml")

def build_prompt_with_context(question: str, results: List[dict]) -> str:
    if results:
        context_snippets = []
        for item in results:
            metadata = item.get("metadata", {})
            title = metadata.get("title", "unknown")
            source = metadata.get("source", "unknown")
            url = metadata.get("url")
            context_snippets.append(
                f"Title: {title}\nSource: {source}\nURL: {url or 'n/a'}\nContent: {item.get('text', '')}"
            )
        context_text = "\n\n---\n\n".join(context_snippets)
    else:
        context_text = "No relevant knowledge was found in the vector store."
    return f"You are a concise assistant. Use the retrieved knowledge from the context below to answer the user's question.\n\nContext:\n{context_text}\n\nQuestion: {question}\nAnswer:" 


def create_document(db: Session, title: str, source: str, doc_type: str, content: str, url: Optional[str] = None) -> Document:
    document = Document(title=title, source=source, doc_type=doc_type, content=content, url=url)
    db.add(document)
    db.commit()
    db.refresh(document)
    add_document_vectors(document.id, title, source, content, url)
    return document


def perform_reindex(db: Session):
    for document in db.query(Document).all():
        delete_document_vectors(document.id)
        add_document_vectors(document.id, document.title, document.source, document.content, document.url)


def find_api(db: Session, identifier: str) -> ApiEntry:
    by_id = db.query(ApiEntry).filter(ApiEntry.id == identifier).first() if identifier.isdigit() else None
    if by_id:
        return by_id
    return db.query(ApiEntry).filter(ApiEntry.name == identifier).first()


def execute_api_call(entry: ApiEntry) -> dict:
    headers = json.loads(entry.headers) if entry.headers else {}
    response = requests.request(entry.method, entry.url, headers=headers, timeout=30)
    return {
        "status_code": response.status_code,
        "headers": dict(response.headers),
        "body": response.text,
    }


def parse_command(content: str, db: Session) -> Optional[dict]:
    text = content.strip()
    if text.startswith("/help"):
        return {"type": "help", "payload": "Available commands: /help, /addtext, /addurl, /reindex, /stats, /apis, /runapi"}
    if text.startswith("/addtext"):
        payload = text[len("/addtext"):].strip()
        return {"type": "addtext", "payload": payload}
    if text.startswith("/addurl"):
        payload = text[len("/addurl"):].strip()
        return {"type": "addurl", "payload": payload}
    if text.startswith("/reindex"):
        return {"type": "reindex"}
    if text.startswith("/stats"):
        return {"type": "stats"}
    if text.startswith("/apis"):
        return {"type": "apis"}
    if text.startswith("/runapi"):
        payload = text[len("/runapi"):].strip()
        return {"type": "runapi", "payload": payload}
    return None


def command_response(command: dict, db: Session) -> str:
    kind = command["type"]
    if kind == "help":
        return command["payload"]
    if kind == "addtext":
        source_text = command["payload"]
        if not source_text:
            raise HTTPException(status_code=400, detail="/addtext requires text after the command.")
        document = create_document(db, title="Chat addition", source="chat", doc_type="text", content=source_text)
        return f"Knowledge added from chat as document {document.id}."
    if kind == "addurl":
        url = command["payload"]
        if not url:
            raise HTTPException(status_code=400, detail="/addurl requires a URL after the command.")
        text = fetch_url_text(url)
        if not text:
            raise HTTPException(status_code=400, detail="Unable to extract text from URL.")
        document = create_document(db, title=url, source="url", doc_type="url", content=text, url=url)
        return f"URL content added as document {document.id}."
    if kind == "reindex":
        perform_reindex(db)
        return "Reindex complete. All documents refreshed in the vector store."
    if kind == "stats":
        return json.dumps(get_stats(db).dict(), indent=2)
    if kind == "apis":
        entries = db.query(ApiEntry).all()
        return json.dumps(
            [{"id": entry.id, "name": entry.name, "url": entry.url, "method": entry.method} for entry in entries],
            indent=2,
        )
    if kind == "runapi":
        identifier = command["payload"]
        if not identifier:
            raise HTTPException(status_code=400, detail="/runapi requires an API name or id.")
        entry = find_api(db, identifier)
        if not entry:
            raise HTTPException(status_code=404, detail="API not found.")
        result = execute_api_call(entry)
        return json.dumps(result, indent=2)
    raise HTTPException(status_code=400, detail="Unknown command.")


def get_stats(db: Session) -> StatsResponse:
    total_documents = db.query(Document).count()
    total_urls = db.query(Document).filter(Document.source == "url").count()
    total_chats = db.query(Conversation).count()
    total_vectors = count_vectors()
    return StatsResponse(
        total_documents=total_documents,
        total_urls=total_urls,
        total_chats=total_chats,
        total_vectors=total_vectors,
    )


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest, db: Session = Depends(get_db)):
    conversation = get_or_create_conversation(db, request.conversation_id)
    record_message(db, conversation, "user", request.prompt)
    command = parse_command(request.prompt, db)
    if command:
        result_text = command_response(command, db)
        record_message(db, conversation, "assistant", result_text)
        return ChatResponse(conversation_id=conversation.id, answer=result_text, sources=[])

    results = query_vectors(request.prompt, limit=RETRIEVAL_COUNT)
    prompt = build_prompt_with_context(request.prompt, results)
    answer = ask_llm(prompt)
    if not answer or not answer.strip():
        logger.error('LLM returned empty reply for chat endpoint; using fallback text')
        answer = 'Sorry, I could not generate a response right now. Please try again later.'
    record_message(db, conversation, "assistant", answer)
    sources = [
        {
            "document_id": item["metadata"].get("document_id"),
            "title": item["metadata"].get("title"),
            "url": item["metadata"].get("url"),
        }
        for item in results
    ]
    return ChatResponse(conversation_id=conversation.id, answer=answer, sources=sources)


@app.post("/chat/stream")
def stream_chat(request: ChatRequest, db: Session = Depends(get_db)):
    conversation = get_or_create_conversation(db, request.conversation_id)
    record_message(db, conversation, "user", request.prompt)
    command = parse_command(request.prompt, db)
    if command:
        result_text = command_response(command, db)
        record_message(db, conversation, "assistant", result_text)
        def command_stream():
            yield f"data: {result_text}\n\n"
        return StreamingResponse(command_stream(), media_type="text/event-stream")

    results = query_vectors(request.prompt, limit=RETRIEVAL_COUNT)
    prompt = build_prompt_with_context(request.prompt, results)
    def event_generator():
        for chunk in stream_llm(prompt):
            yield chunk
        record_message(db, conversation, "assistant", "[streamed response]")
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/upload", response_model=DocumentRecord)
def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    temp_path = save_upload_temp(file)
    try:
        content = extract_text_from_file(temp_path, file.filename)
        if not content:
            raise HTTPException(status_code=400, detail="Unable to extract text from file.")
        document = create_document(db, title=file.filename, source="file", doc_type=file.filename.rsplit('.', 1)[-1], content=content)
        return document
    finally:
        try:
            import os
            os.remove(temp_path)
        except OSError:
            pass


@app.post("/add-text")
def add_text(content: str, db: Session = Depends(get_db)):
    if not content.strip():
        raise HTTPException(status_code=400, detail="Text is required.")
    document = create_document(db, title="Manual text", source="chat", doc_type="text", content=content)
    return {"message": "Text added.", "document_id": document.id}


@app.post("/add-url")
def add_url(url: str, db: Session = Depends(get_db)):
    content = fetch_url_text(url)
    if not content:
        raise HTTPException(status_code=400, detail="Unable to extract text from URL.")
    document = create_document(db, title=url, source="url", doc_type="url", content=content, url=url)
    return {"message": "URL added.", "document_id": document.id}


@app.post("/run-api")
def run_api(api_id: str, db: Session = Depends(get_db)):
    entry = find_api(db, api_id)
    if not entry:
        raise HTTPException(status_code=404, detail="API not found.")
    return execute_api_call(entry)


@app.get("/stats", response_model=StatsResponse)
def stats(db: Session = Depends(get_db)):
    return get_stats(db)


@app.get("/documents", response_model=List[DocumentRecord])
def list_documents(db: Session = Depends(get_db)):
    documents = db.query(Document).order_by(Document.created_at.desc()).all()
    return documents


@app.delete("/document/{document_id}")
def delete_document(document_id: int, db: Session = Depends(get_db)):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    delete_document_vectors(document.id)
    db.delete(document)
    db.commit()
    return {"message": "Document deleted."}


@app.get("/apis", response_model=List[ApiEntrySchema])
def list_apis(db: Session = Depends(get_db)):
    return db.query(ApiEntry).all()


@app.post("/apis", response_model=ApiEntrySchema)
def create_api(entry: ApiEntrySchema, db: Session = Depends(get_db)):
    db_entry = ApiEntry(name=entry.name, url=str(entry.url), method=entry.method.upper(), headers=json.dumps(entry.headers or {}))
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    return db_entry


@app.put("/apis/{api_id}", response_model=ApiEntrySchema)
def update_api(api_id: int, entry: ApiEntrySchema, db: Session = Depends(get_db)):
    db_entry = db.query(ApiEntry).filter(ApiEntry.id == api_id).first()
    if not db_entry:
        raise HTTPException(status_code=404, detail="API not found.")
    db_entry.name = entry.name
    db_entry.url = str(entry.url)
    db_entry.method = entry.method.upper()
    db_entry.headers = json.dumps(entry.headers or {})
    db.commit()
    db.refresh(db_entry)
    return db_entry


@app.delete("/apis/{api_id}")
def delete_api(api_id: int, db: Session = Depends(get_db)):
    entry = db.query(ApiEntry).filter(ApiEntry.id == api_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="API not found.")
    db.delete(entry)
    db.commit()
    return {"message": "API deleted."}


@app.get("/settings", response_model=List[SettingSchema])
def get_settings(db: Session = Depends(get_db)):
    return db.query(Setting).all()


@app.put("/settings")
def update_setting(setting: SettingSchema, db: Session = Depends(get_db)):
    db_entry = db.query(Setting).filter(Setting.key == setting.key).first()
    if db_entry:
        db_entry.value = setting.value
    else:
        db_entry = Setting(key=setting.key, value=setting.value)
        db.add(db_entry)
    db.commit()
    return {"message": "Setting updated."}
