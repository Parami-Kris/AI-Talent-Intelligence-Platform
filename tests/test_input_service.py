import pytest

from backend.app.services.input_service import (
    detect_format,
    extract_text_from_upload,
    load_json_file,
    load_text_file,
    normalize_uploaded_text_or_json,
)


def test_detect_format_accepts_supported_extensions():
    assert detect_format("resume.pdf") == ".pdf"
    assert detect_format("notes.TXT") == ".txt"


def test_detect_format_rejects_unsupported_extension():
    with pytest.raises(ValueError):
        detect_format("resume.exe")


def test_load_text_file_reads_contents(tmp_path):
    file_path = tmp_path / "note.txt"
    file_path.write_text("hello world", encoding="utf-8")

    assert load_text_file(file_path) == "hello world"


def test_load_json_file_reads_contents(tmp_path):
    file_path = tmp_path / "data.json"
    file_path.write_text('{"a": 1}', encoding="utf-8")

    assert load_json_file(file_path) == {"a": 1}


def test_normalize_uploaded_text_or_json_handles_json_bytes():
    result = normalize_uploaded_text_or_json(b'{"a": 1}', "data.json")
    assert result == {"a": 1}


def test_normalize_uploaded_text_or_json_handles_text_bytes():
    result = normalize_uploaded_text_or_json(b"hello", "notes.txt")
    assert result == "hello"


def test_normalize_uploaded_text_or_json_rejects_pdf_bytes():
    with pytest.raises(ValueError):
        normalize_uploaded_text_or_json(b"%PDF-1.4", "resume.pdf")


def test_extract_text_from_upload_handles_text_bytes():
    assert extract_text_from_upload(b"hello world", "notes.txt") == "hello world"


def test_extract_text_from_upload_rejects_json():
    with pytest.raises(ValueError):
        extract_text_from_upload(b'{"a": 1}', "data.json")