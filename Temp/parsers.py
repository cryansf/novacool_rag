from typing import Optional
from pypdf import PdfReader
from docx import Document

def pdf_to_text(path: str) -> str:
    reader = PdfReader(path)
    parts = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n\n".join(parts)

def docx_to_text(path: str) -> str:
    d = Document(path)
    return "\n".join(p.text for p in d.paragraphs)

def any_to_text(path: str) -> Optional[str]:
    p = path.lower()
    if p.endswith('.pdf'):
        return pdf_to_text(path)
    if p.endswith('.docx'):
        return docx_to_text(path)
    if p.endswith('.txt'):
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    return None
