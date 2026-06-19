import os
import chromadb
from chromadb.utils import embedding_functions
from .config import CHROMA_DIR, CHUNK_SIZE
from .utils import chunk_text

client = chromadb.PersistentClient(path=CHROMA_DIR)
embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
collection = client.get_or_create_collection(name="knowledge", embedding_function=embedding_function)


def persist_vectors():
    try:
        persist_fn = getattr(client, 'persist', None)
        if callable(persist_fn):
            persist_fn()
    except Exception:
        # Some chromadb client implementations (SegmentAPI) don't expose persist;
        # failing to persist should not crash the application.
        pass


def add_document_vectors(document_id: int, title: str, source: str, text: str, url: str | None = None):
    chunks = []
    chunk_count = 0
    for chunk in chunk_text(text):
        chunk_count += 1
        chunks.append(chunk)
    if not chunks:
        return
    ids = [f"{document_id}-{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "document_id": str(document_id),
            "title": title,
            "source": source,
            "url": url or "",
            "chunk_index": i,
        }
        for i in range(len(chunks))
    ]
    collection.add(
        documents=chunks,
        metadatas=metadatas,
        ids=ids,
    )
    persist_vectors()


def query_vectors(query: str, limit: int = 4):
    results = collection.query(
        query_texts=[query],
        n_results=limit,
        include=['metadatas', 'distances', 'documents'],
    )
    if not results or not results.get('metadatas'):
        return []
    rows = []
    for metadata, document, distance in zip(results['metadatas'][0], results['documents'][0], results['distances'][0]):
        rows.append({
            'metadata': metadata,
            'text': document,
            'distance': distance,
        })
    return rows


def delete_document_vectors(document_id: int):
    try:
        collection.delete(where={"document_id": [str(document_id)]})
        persist_vectors()
    except Exception:
        pass


def count_vectors() -> int:
    info = collection.count()
    if isinstance(info, dict):
        return int(info.get('count', 0))
    try:
        return int(info)
    except Exception:
        return 0
