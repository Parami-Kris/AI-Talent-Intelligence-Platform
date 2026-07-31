from backend.app.services import job_matching_service


def _jobs(count):
    return [{"source": "brightdata", "id": str(i), "title": f"Job {i}", "company": "Acme", "description": "desc"} for i in range(count)]


def test_score_jobs_for_resume_attaches_match_scores(monkeypatch):
    monkeypatch.setattr(
        job_matching_service,
        "chat_completion_json",
        lambda *a, **k: {"scores": [{"job_index": 0, "match_percentage": 88, "match_reason": "Strong fit."}]},
    )

    scored = job_matching_service.score_jobs_for_resume({"normalized_skills": ["Python"]}, _jobs(1))

    assert scored[0]["match_percentage"] == 88
    assert scored[0]["match_reason"] == "Strong fit."
    assert scored[0]["title"] == "Job 0"


def test_score_jobs_for_resume_caps_batch_size(monkeypatch):
    captured = {}

    def fake_chat_completion_json(prompt, **kwargs):
        captured["prompt"] = prompt
        return {"scores": []}

    monkeypatch.setattr(job_matching_service, "chat_completion_json", fake_chat_completion_json)

    scored = job_matching_service.score_jobs_for_resume({}, _jobs(50))

    assert len(scored) == job_matching_service.JOB_MATCH_BATCH_CAP
    assert "Job 24" in captured["prompt"]
    assert "Job 25" not in captured["prompt"]


def test_score_jobs_for_resume_marks_unscored_when_llm_unavailable(monkeypatch):
    monkeypatch.setattr(job_matching_service, "chat_completion_json", lambda *a, **k: None)

    scored = job_matching_service.score_jobs_for_resume({}, _jobs(2))

    assert all(job["match_percentage"] is None for job in scored)
    assert all(job["match_reason"] is None for job in scored)


def test_score_jobs_for_resume_returns_empty_list_for_no_jobs(monkeypatch):
    monkeypatch.setattr(job_matching_service, "chat_completion_json", lambda *a, **k: {"scores": []})

    assert job_matching_service.score_jobs_for_resume({}, []) == []


def test_score_jobs_for_resume_truncates_long_descriptions(monkeypatch):
    captured = {}

    def fake_chat_completion_json(prompt, **kwargs):
        captured["prompt"] = prompt
        return {"scores": []}

    monkeypatch.setattr(job_matching_service, "chat_completion_json", fake_chat_completion_json)

    long_description = "x" * 1000
    job_matching_service.score_jobs_for_resume({}, [{"source": "s", "id": "1", "title": "T", "description": long_description}])

    assert "x" * 1000 not in captured["prompt"]
    assert "x" * 600 in captured["prompt"]
