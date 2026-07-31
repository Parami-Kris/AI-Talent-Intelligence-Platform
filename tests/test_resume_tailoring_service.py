from backend.app.services import resume_tailoring_service

_JD = {"job_title": "Backend Engineer", "required_skills": ["Python"], "experience_required": "2 years"}
_CANDIDATE = {
    "name": "Alice",
    "raw_text": "very long original resume text that shouldn't be duplicated into the prompt" * 20,
    "experience": [{"job_title": "Engineer", "duration": "Jan 2022 - Present", "description": "Built REST APIs with Flask"}],
    "normalized_skills": ["Python"],
    "education": [],
}


def test_tailor_resume_returns_llm_result(monkeypatch):
    monkeypatch.setattr(
        resume_tailoring_service,
        "chat_completion_json",
        lambda *a, **k: {
            "tailored_resume_text": "Tailored text",
            "summary_of_changes": ["Added Flask to skills - demonstrated in your Engineer role."],
        },
    )

    result = resume_tailoring_service.tailor_resume(_JD, _CANDIDATE)

    assert result["tailored_resume_text"] == "Tailored text"
    assert result["summary_of_changes"] == ["Added Flask to skills - demonstrated in your Engineer role."]


def test_tailor_resume_returns_none_text_when_llm_unavailable(monkeypatch):
    monkeypatch.setattr(resume_tailoring_service, "chat_completion_json", lambda *a, **k: None)

    result = resume_tailoring_service.tailor_resume(_JD, _CANDIDATE)

    assert result["tailored_resume_text"] is None
    assert result["summary_of_changes"] == []


def test_tailor_resume_excludes_raw_text_from_prompt(monkeypatch):
    captured = {}

    def fake_chat_completion_json(prompt, **kwargs):
        captured["prompt"] = prompt
        return {"tailored_resume_text": "x", "summary_of_changes": []}

    monkeypatch.setattr(resume_tailoring_service, "chat_completion_json", fake_chat_completion_json)

    resume_tailoring_service.tailor_resume(_JD, _CANDIDATE)

    assert "very long original resume text" not in captured["prompt"]
    assert "Built REST APIs with Flask" in captured["prompt"]


def test_tailor_resume_grounds_prompt_in_deterministic_gap_analysis(monkeypatch):
    captured = {}

    def fake_chat_completion_json(prompt, **kwargs):
        captured["prompt"] = prompt
        return {"tailored_resume_text": "x", "summary_of_changes": []}

    monkeypatch.setattr(resume_tailoring_service, "chat_completion_json", fake_chat_completion_json)

    resume_tailoring_service.tailor_resume(_JD, _CANDIDATE)

    # analyze_profile_gap's qualification_gaps output should be embedded, not just
    # the raw jd/candidate - confirms the grounding call actually happened.
    assert "matched_skills" in captured["prompt"]
