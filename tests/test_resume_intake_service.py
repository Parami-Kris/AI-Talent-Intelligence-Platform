import backend.app.services.resume_intake_service as intake


def test_parse_resume_upload_wires_extraction_together(monkeypatch):
    monkeypatch.setattr(intake, "extract_text_from_upload", lambda content, filename: "resume text")
    monkeypatch.setattr(
        intake,
        "extract_structured_resume",
        lambda text: {"name": "Jane Doe", "normalized_skills": ["Python"]},
    )

    result = intake.parse_resume_upload(b"bytes", "jane.pdf")

    assert result["name"] == "Jane Doe"
    assert result["normalized_skills"] == ["Python"]
    assert result["raw_text"] == "resume text"
    assert "error" not in result


def test_parse_resume_upload_raises_on_llm_error(monkeypatch):
    monkeypatch.setattr(intake, "extract_text_from_upload", lambda content, filename: "resume text")
    monkeypatch.setattr(
        intake,
        "extract_structured_resume",
        lambda text: {"error": "bad json", "raw_response": "not json"},
    )

    try:
        intake.parse_resume_upload(b"bytes", "broken.pdf")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "broken.pdf" in str(exc)


def test_parse_jd_upload_raises_on_llm_error(monkeypatch):
    monkeypatch.setattr(intake, "extract_text_from_upload", lambda content, filename: "jd text")
    monkeypatch.setattr(
        intake,
        "extract_structured_jd",
        lambda text: {"error": "bad json", "raw_response": "not json"},
    )

    try:
        intake.parse_jd_upload(b"bytes", "jd.txt")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "jd.txt" in str(exc)
        assert "bad json" in str(exc)


def test_parse_resumes_batch_isolates_failures(monkeypatch):
    def fake_parse(content, filename):
        if filename == "bad.pdf":
            raise ValueError(f"Failed to parse resume '{filename}': boom")
        return {"name": filename}

    monkeypatch.setattr(intake, "parse_resume_upload", fake_parse)

    result = intake.parse_resumes_batch([
        (b"1", "good.pdf"),
        (b"2", "bad.pdf"),
    ])

    assert len(result["candidates"]) == 1
    assert result["candidates"][0]["name"] == "good.pdf"
    assert len(result["failures"]) == 1
    assert result["failures"][0]["filename"] == "bad.pdf"


def test_parse_resumes_batch_reports_progress_per_file(monkeypatch):
    def fake_parse(content, filename):
        if filename == "bad.pdf":
            raise ValueError("boom")
        return {"name": filename}

    monkeypatch.setattr(intake, "parse_resume_upload", fake_parse)

    events = []
    intake.parse_resumes_batch(
        [(b"1", "good.pdf"), (b"2", "bad.pdf")],
        on_progress=lambda **kwargs: events.append(kwargs),
    )

    assert events == [
        {"current_filename": "good.pdf"},
        {"processed_increment": True},
        {"current_filename": "bad.pdf"},
        {"processed_increment": True},
    ]