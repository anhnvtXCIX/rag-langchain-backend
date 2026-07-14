from pathlib import Path

from docx import Document as DocxDocument
from pypdf import PdfReader

from app.rag.errors import TextExtractionError


# Synchronous on purpose: parsing is blocking work, so callers must run this
# via anyio.to_thread to keep it off the event loop.
def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        text = path.read_text(encoding="utf-8", errors="replace")
    elif suffix == ".pdf":
        reader = PdfReader(path)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    elif suffix == ".docx":
        docx = DocxDocument(str(path))
        text = "\n".join(paragraph.text for paragraph in docx.paragraphs)
    else:
        raise TextExtractionError(f"Unsupported file extension: {suffix}")

    if not text.strip():
        raise TextExtractionError(f"No text could be extracted from {path.name}")
    return text
