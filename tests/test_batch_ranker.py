import pytest

from pipeline import batch_ranker
from pipeline.batch_ranker import (
    batch_education_match,
    batch_experience_match,
    build_summary,
    duration_years,
    job_stability_signal,
    minimum_required_years,
    rank_candidates,
    ranking_key,
)
from tests._fakes import FakeGenAIClient


def test_minimum_required_years_parses_leading_number():
    assert minimum_required_years("5+ years") == 5
    assert minimum_required_years("") == 0
    assert minimum_required_years(None) == 0


def test_duration_years_computes_span_inclusive():
    assert duration_years("Jan 2020 - Dec 2020") == pytest.approx(1.0)


def test_duration_years_handles_present():
    years = duration_years("Jan 2020 - Present")
    assert years > 0


def test_duration_years_returns_zero_for_unparseable():
    assert duration_years("") == 0
    assert duration_years("sometime a while ago") == 0


def test_batch_experience_match_meets_requirement():
    candidate = {
        "experience": [
            {"job_title": "Engineer", "company": "Acme", "duration": "Jan 2018 - Jan 2023"}
        ]
    }
    jd = {"experience_required": "3 years"}

    result = batch_experience_match(candidate, jd)

    assert result["matches_requirements"] is True
    assert result["score"] == 100


def test_batch_experience_match_falls_short():
    candidate = {
        "experience": [
            {"job_title": "Engineer", "company": "Acme", "duration": "Jan 2022 - Jan 2023"}
        ]
    }
    jd = {"experience_required": "5 years"}

    result = batch_experience_match(candidate, jd)

    assert result["matches_requirements"] is False
    assert result["score"] < 100


def test_rank_candidates_orders_eligible_first_without_llm_calls():
    jd = {
        "job_title": "Backend Engineer",
        "required_skills": ["Python"],
        "preferred_skills": [],
        "experience_required": "1 year",
        "education_required": "",
    }
    candidates = [
        {
            "name": "Weak Candidate",
            "normalized_skills": [],
            "experience": [],
        },
        {
            "name": "Strong Candidate",
            "normalized_skills": ["Python"],
            "experience": [
                {"job_title": "Dev", "company": "Acme", "duration": "Jan 2020 - Jan 2023"}
            ],
        },
    ]

    ranked = rank_candidates(candidates, jd)

    assert ranked[0]["candidate_name"] == "Strong Candidate"
    assert ranked[0]["is_eligible"] is True
    assert ranked[1]["candidate_name"] == "Weak Candidate"

    summary = build_summary(ranked)
    assert summary[0]["rank"] == 1
    assert ranking_key(ranked[0]) > ranking_key(ranked[1])


def test_job_stability_signal_flags_frequent_short_stints():
    candidate = {
        "experience": [
            {"duration": "Jan 2020 - Jun 2020"},
            {"duration": "Jul 2020 - Jan 2021"},
            {"duration": "Feb 2021 - Sep 2021"},
        ]
    }

    signal = job_stability_signal(candidate)

    assert signal["job_count"] == 3
    assert signal["short_stints_count"] == 3
    assert signal["flag"] == "frequent_job_changes"


def test_job_stability_signal_marks_long_tenures_stable():
    candidate = {
        "experience": [
            {"duration": "Jan 2015 - Jan 2019"},
            {"duration": "Feb 2019 - Present"},
        ]
    }

    signal = job_stability_signal(candidate)

    assert signal["job_count"] == 2
    assert signal["short_stints_count"] == 0
    assert signal["flag"] == "stable"


def test_job_stability_signal_handles_no_experience():
    signal = job_stability_signal({"experience": []})

    assert signal["flag"] == "insufficient_data"
    assert signal["job_count"] == 0
    assert signal["average_tenure_years"] is None


def test_rank_candidates_attaches_job_stability():
    jd = {
        "job_title": "Backend Engineer",
        "required_skills": ["Python"],
        "preferred_skills": [],
        "experience_required": "1 year",
        "education_required": "",
    }
    candidates = [
        {"name": "Weak Candidate", "normalized_skills": [], "experience": []},
        {
            "name": "Strong Candidate",
            "normalized_skills": ["Python"],
            "experience": [{"job_title": "Dev", "company": "Acme", "duration": "Jan 2020 - Jan 2023"}],
        },
    ]

    ranked = rank_candidates(candidates, jd)
    summary = build_summary(ranked)

    strong = next(r for r in summary if r["candidate_name"] == "Strong Candidate")
    weak = next(r for r in summary if r["candidate_name"] == "Weak Candidate")
    assert strong["job_stability_flag"] == "stable"
    assert weak["job_stability_flag"] == "insufficient_data"


def test_batch_education_match_success_parses_response(monkeypatch):
    fake_text = (
        '[{"candidate_index": 0, "candidate_name": "Alice", "score": 100, '
        '"status": "matched", "reason": "Meets requirement.", '
        '"matched": ["Bachelor\'s degree"], "missing": [], "evidence": []}]'
    )
    monkeypatch.setattr(batch_ranker, "client", FakeGenAIClient(response_text=fake_text))

    candidates = [{"name": "Alice", "education": [{"degree": "BSc"}]}]
    jd = {"education_required": "Bachelor's degree"}

    results = batch_education_match(candidates, jd)

    assert results[0]["score"] == 100
    assert results[0]["status"] == "matched"


def test_batch_education_match_malformed_json_falls_back_to_default_for_all_candidates(monkeypatch):
    monkeypatch.setattr(batch_ranker, "client", FakeGenAIClient(response_text="not json"))

    candidates = [
        {"name": "Alice", "education": [{"degree": "BSc"}]},
        {"name": "Bob", "education": [{"degree": "MSc"}]},
    ]
    jd = {"education_required": "Bachelor's degree"}

    results = batch_education_match(candidates, jd)

    assert len(results) == 2
    for result in results:
        assert result["status"] == "not_specified"
        assert result["score"] is None


def test_batch_education_match_short_circuits_when_education_required_is_none():
    # Regression: this crashed in production against a real Gemini-parsed JD
    # that returned {"education_required": null} (present key, None value) -
    # jd.get("education_required", "").strip() doesn't fall back to "" for a
    # present-but-None value. No client call should happen here at all.
    candidates = [{"name": "Alice", "education": []}, {"name": "Bob", "education": []}]
    jd = {"education_required": None}

    results = batch_education_match(candidates, jd)

    assert len(results) == 2
    for result in results:
        assert result["status"] == "not_specified"
        assert result["score"] is None


def test_batch_education_match_short_circuits_on_placeholder_text():
    candidates = [{"name": "Alice", "education": [{"degree": "BSc"}]}]
    jd = {"education_required": "Not specified"}

    results = batch_education_match(candidates, jd)

    assert results[0]["status"] == "not_specified"
    assert results[0]["score"] is None


def test_rank_candidates_attaches_deterministic_education_summary():
    jd = {
        "job_title": "Backend Engineer",
        "required_skills": [],
        "preferred_skills": [],
        "experience_required": "",
        "education_required": "",
    }
    candidates = [
        {
            "name": "Alice",
            "normalized_skills": [],
            "experience": [],
            "education": [{"degree": "B.Tech", "institution": "IIT Kharagpur", "year": "2020"}],
        }
    ]

    ranked = rank_candidates(candidates, jd)

    assert ranked[0]["education_summary"] == ["B.Tech from IIT Kharagpur (2020)"]


def test_rank_candidates_carries_raw_text_through_for_detail_view():
    jd = {
        "job_title": "Backend Engineer",
        "required_skills": [],
        "preferred_skills": [],
        "experience_required": "",
        "education_required": "",
    }
    candidates = [
        {"name": "Alice", "normalized_skills": [], "experience": [], "raw_text": "Alice's full resume text"},
        {"name": "Bob", "normalized_skills": [], "experience": []},
    ]

    ranked = rank_candidates(candidates, jd)

    alice = next(r for r in ranked if r["candidate_name"] == "Alice")
    bob = next(r for r in ranked if r["candidate_name"] == "Bob")
    assert alice["raw_text"] == "Alice's full resume text"
    assert bob["raw_text"] is None