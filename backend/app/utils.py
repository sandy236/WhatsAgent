import os
import re
import tempfile
import requests
from bs4 import BeautifulSoup
import pdfplumber
import docx
from .config import CHUNK_SIZE

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "md"}


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_text_from_file(file_path: str, filename: str) -> str:
    extension = filename.rsplit(".", 1)[-1].lower()
    if extension == "pdf":
        text = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                text.append(page_text)
        return clean_text("\n\n".join(text))
    if extension == "docx":
        doc = docx.Document(file_path)
        return clean_text("\n\n".join(p.text for p in doc.paragraphs if p.text))
    if extension in {"txt", "md"}:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return clean_text(f.read())
    raise ValueError("Unsupported file type")


def fetch_url_text(url: str) -> str:
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")
    for selector in ["nav", "footer", "header", "script", "style"]:
        for node in soup.select(selector):
            node.decompose()
    title = soup.title.string if soup.title else ""
    paragraphs = [p.get_text(separator=" ", strip=True) for p in soup.find_all(["p", "h1", "h2", "h3", "li"])]
    body = "\n\n".join(p for p in paragraphs if p)
    content = f"{title}\n\n{body}" if title else body
    return clean_text(content)


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = 100):
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(clean_text(chunk))
        start = max(end - overlap, end)
    return [chunk for chunk in chunks if chunk]


def save_upload_temp(upload_file) -> str:
    suffix = os.path.splitext(upload_file.filename)[-1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(upload_file.file.read())
        return tmp.name
