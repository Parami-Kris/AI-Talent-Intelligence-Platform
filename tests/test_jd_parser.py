from pipeline import jd_parser
from pipeline.jd_parser import extract_structured_jd
from tests._fakes import FakeGenAIClient


def test_extract_structured_jd_success_parses_response(monkeypatch):
    fake_text = (
        '{"job_title": "Backend Engineer", "required_skills": ["Python"], '
        '"preferred_skills": [], "skill_categories": {}, "experience_required": "2 years", '
        '"education_required": "", "responsibilities": []}'
    )
    monkeypatch.setattr(jd_parser, "client", FakeGenAIClient(response_text=fake_text))

    result = extract_structured_jd("some job description text")

    assert result["job_title"] == "Backend Engineer"
    assert result["required_skills"] == ["Python"]


def test_extract_structured_jd_malformed_json_returns_error_dict(monkeypatch):
    monkeypatch.setattr(jd_parser, "client", FakeGenAIClient(response_text="not json"))

    result = extract_structured_jd("some job description text")

    assert "error" in result
    assert result["raw_response"] == "not json"
