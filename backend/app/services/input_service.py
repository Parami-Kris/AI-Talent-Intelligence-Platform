import json
import os
import tempfile
from pathlib import Path
from typing import Any

from docling.document_converter import DocumentConverter


SUPPORTED_TEXT_FORMATS = {".txt", ".md"}
SUPPORTED_JSON_FORMATS = {".json"}
SUPPORTED_DOCUMENT_FORMATS = {".pdf", ".docx", ".doc"}
SUPPORTED_FORMATS = SUPPORTED_TEXT_FORMATS | SUPPORTED_JSON_FORMATS | SUPPORTED_DOCUMENT_FORMATS


def detect_format(file_path: str | Path) -> str:
    suffix = Path(file_path).suffix.lower()
    if suffix not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported input format: {suffix or 'unknown'}")
    return suffix


def load_json_file(file_path: str | Path) -> dict[str, Any] | list[dict[str, Any]]:
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_text_file(file_path: str | Path) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def extract_document_text(file_path: str | Path) -> str:
    converter = DocumentConverter()
    result = converter.convert(str(file_path))
    return result.document.export_to_text()


def load_input(file_path: str | Path) -> dict[str, Any] | list[dict[str, Any]] | str:
    file_format = detect_format(file_path)

    if file_format in SUPPORTED_JSON_FORMATS:
        return load_json_file(file_path)

    if file_format in SUPPORTED_TEXT_FORMATS:
        return load_text_file(file_path)

    return extract_document_text(file_path)


def normalize_uploaded_text_or_json(
    content: bytes,
    filename: str,
) -> dict[str, Any] | list[dict[str, Any]] | str:
    file_format = detect_format(filename)

    if file_format in SUPPORTED_JSON_FORMATS:
        return json.loads(content.decode("utf-8"))

    if file_format in SUPPORTED_TEXT_FORMATS:
        return content.decode("utf-8")

    raise ValueError(
        "PDF/DOCX uploads require saving to a temporary file before text extraction."
    )


def extract_text_from_upload(content: bytes, filename: str) -> str:
    file_format = detect_format(filename)

    if file_format in SUPPORTED_TEXT_FORMATS:
        return content.decode("utf-8")

    if file_format in SUPPORTED_JSON_FORMATS:
        raise ValueError("JSON uploads are already structured; use load_json_file instead.")

    suffix = Path(filename).suffix
    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as tmp_file:
            tmp_file.write(content)
        return extract_document_text(tmp_path)
    finally:
        os.unlink(tmp_path)
