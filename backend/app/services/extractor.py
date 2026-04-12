from pathlib import Path
from typing import Any, Optional

import numpy as np
from docx import Document


_reader: Optional[Any] = None


def _get_ocr_reader() -> Any:
    """Initialize EasyOCR once and reuse it across requests."""
    global _reader
    if _reader is None:
        try:
            import easyocr  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ImportError("easyocr is required for image resume extraction.") from exc
        _reader = easyocr.Reader(["en"], gpu=False)
    return _reader


def extract_text_from_pdf(file_path: Path) -> str:
    """Extract text from PDF; fallback to OCR for scanned/image-based pages."""
    try:
        import fitz
    except ImportError as exc:
        raise ImportError("PyMuPDF is required for PDF extraction.") from exc

    text_chunks = []
    page_images = []
    with fitz.open(file_path) as doc:
        for page in doc:
            page_text = str(page.get_text("text") or "")
            if page_text.strip():
                text_chunks.append(page_text)
                continue

            # Rasterize pages with no embedded text for OCR fallback.
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            page_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            page_images.append(page_array)

    direct_text = "\n".join(text_chunks).strip()
    if direct_text:
        return direct_text

    if not page_images:
        return ""

    reader = _get_ocr_reader()
    ocr_chunks = []
    for image in page_images:
        result = reader.readtext(image, detail=0, paragraph=True)
        if result:
            ocr_chunks.append("\n".join(result))

    return "\n".join(ocr_chunks).strip()


def extract_text_from_image(file_path: Path) -> str:
    """Extract text from image resumes using EasyOCR."""
    reader = _get_ocr_reader()
    result = reader.readtext(str(file_path), detail=0, paragraph=True)
    return "\n".join(result).strip()


def extract_resume_text(file_path: Path) -> str:
    """Route extraction based on file extension."""
    extension = file_path.suffix.lower().lstrip(".")
    if extension == "pdf":
        return extract_text_from_pdf(file_path)
    if extension in {"png", "jpg", "jpeg", "webp"}:
        return extract_text_from_image(file_path)
    if extension == "docx":
        return extract_text_from_docx(file_path)
    if extension == "txt":
        return extract_text_from_txt(file_path)
    raise ValueError("Unsupported file format. Supported: PDF, DOCX, TXT, PNG, JPG, JPEG, WEBP")


def extract_text_from_docx(file_path: Path) -> str:
    """Extract text from DOCX files."""
    try:
        doc = Document(file_path)
        text_chunks = []
        for para in doc.paragraphs:
            if para.text.strip():
                text_chunks.append(para.text)
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip():
                        text_chunks.append(cell.text)
        return "\n".join(text_chunks).strip()
    except Exception as exc:
        raise ValueError(f"Failed to extract DOCX: {exc}") from exc


def extract_text_from_txt(file_path: Path) -> str:
    """Extract text from plain TXT files."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except UnicodeDecodeError:
        # Try different encoding
        try:
            with open(file_path, "r", encoding="latin-1") as f:
                return f.read().strip()
        except Exception as exc:
            raise ValueError(f"Failed to extract TXT: {exc}") from exc
