import os
import re
from pathlib import Path
from typing import List

from app.config import CHUNK_OVERLAP, MAX_CHUNK_SIZE

try:
    import pymupdf
except ImportError:  # pragma: no cover
    pymupdf = None


def extract_text_from_pdf(file_path: str) -> str:
    if pymupdf is None:
        raise RuntimeError("PyMuPDF is not installed. Install requirements to parse PDF files.")

    pages = []
    with pymupdf.open(file_path) as document:
        for page in document:
            pages.append(page.get_text("text") or "")
    return "\n\n".join(pages)


def extract_pdf_images(file_path: str) -> list[dict]:
    if pymupdf is None:
        raise RuntimeError("PyMuPDF is not installed. Install requirements to parse PDF files.")

    images = []
    with pymupdf.open(file_path) as document:
        for page_number, page in enumerate(document, start=1):
            for image_index, image_info in enumerate(page.get_images(full=True)):
                xref = image_info[0]
                extracted = document.extract_image(xref)
                images.append(
                    {
                        "page_number": page_number,
                        "image_index": image_index,
                        "image_name": f"image_{xref}.{extracted['ext']}",
                        "data": extracted["image"],
                    }
                )
    return images


def chunk_text(
    text: str, chunk_size: int = MAX_CHUNK_SIZE, overlap: int = CHUNK_OVERLAP
) -> List[str]:
    return [
        chunk["content"]
        for chunk in chunk_text_with_locations(text, chunk_size, overlap)
    ]


def chunk_text_with_locations(
    text: str, chunk_size: int = MAX_CHUNK_SIZE, overlap: int = CHUNK_OVERLAP
) -> list[dict]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero.")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size.")

    tokens = list(re.finditer(r"\S+", text))
    if not tokens:
        return []

    normalized_parts = []
    original_positions = []
    for token_index, match in enumerate(tokens):
        if token_index:
            normalized_parts.append(" ")
            original_positions.append(match.start())
        normalized_parts.append(match.group())
        original_positions.extend(range(match.start(), match.end()))

    normalized = "".join(normalized_parts)
    chunks = []
    start = 0
    while start < len(normalized):
        end = min(len(normalized), start + chunk_size)
        content = normalized[start:end]
        content_start = start + len(content) - len(content.lstrip())
        content_end = start + len(content.rstrip()) - 1
        if content_start > content_end:
            content_start, content_end = start, end - 1
        original_start = original_positions[content_start]
        original_end = original_positions[content_end]
        chunks.append(
            {
                "content": content,
                "line_start": text.count("\n", 0, original_start) + 1,
                "line_end": text.count("\n", 0, original_end) + 1,
            }
        )
        if end >= len(normalized):
            break
        start = end - overlap
    return chunks


def save_uploaded_file(uploaded_file, destination_dir: Path) -> str:
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination_path = destination_dir / uploaded_file.filename
    with open(destination_path, "wb") as f:
        f.write(uploaded_file.file.read())
    return str(destination_path)


def read_document_text(file_path: str) -> str:
    suffix = Path(file_path).suffix.lower()
    if suffix == ".pdf":
        return extract_text_from_pdf(file_path)
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()
