from pipeline import matcher
from pipeline.matcher import (
    analyze_match,
    contains_skill_text,
    education_match,
    eligibility_match,
    experience_match,
    normalize_skill,
    overall_match,
    skill_match,
)
from tests._fakes import FakeGenAIClient


def test_normalize_skill_strips_punctuation_and_case():
    assert normalize_skill("Node.js") == "nodejs"
    assert normalize_skill("C++") == "c"


def test_contains_skill_text_matches_word_boundary():
    assert contains_skill_text("Built APIs with Python and FastAPI", "Python")
    assert not contains_skill_text("No relevant tools mentioned here", "Python")


def test_skill_match_scores_required_and_preferred():
    resume = {"normalized_skills": ["Python", "Docker", "SQL"]}
    jd = {
        "required_skills": ["Python", "AWS"],
        "preferred_skills": ["Docker"],
    }

    result = skill_match(resume, jd)

    assert "Python" in result["matched"]
    assert "Docker" in result["matched"]
    assert "AWS" in result["missing"]
    # denominator = 2*2 + 1 = 5, common=1(Python)*2 + preferred=1(Docker) = 3 -> 60%
    assert result["score"] == 60.0


def test_skill_match_handles_no_requirements():
    result = skill_match({"normalized_skills": []}, {})
    assert result["score"] == 0


def test_skill_match_handles_none_values_from_llm_jd_parse():
    # The JD parser (Gemini) can return `null` for a field instead of omitting
    # it or using an empty list/string - .get(key, default) only falls back to
    # the default when the key is *absent*, not when its value is None, so
    # these fields need defensive handling (regression: crashed in production
    # with `AttributeError: 'NoneType' object has no attribute 'strip'`).
    resume = {"normalized_skills": None}
    jd = {"required_skills": None, "preferred_skills": None}

    result = skill_match(resume, jd)

    assert result["score"] == 0
    assert result["matched"] == []


def test_eligibility_match_flags_missing_must_haves():
    skill_result = {
        "required_skills": ["Python", "AWS"],
        "common_skills": ["Python"],
    }
    exp_result = {"matches_requirements": False}

    eligibility = eligibility_match(skill_result, exp_result)

    assert eligibility["meets_experience"] is False
    assert eligibility["missing_must_haves"] == ["AWS"]


def test_overall_match_weights_without_education():
    skill_result = {"score": 80}
    exp_result = {"score": 60}
    edu_result = {"score": None}

    result = overall_match(skill_result, edu_result, exp_result)

    assert result["overall_score"] == round(80 * 0.625 + 60 * 0.375, 2)


def test_overall_match_weights_with_education():
    skill_result = {"score": 80}
    exp_result = {"score": 60}
    edu_result = {"score": 100}

    result = overall_match(skill_result, edu_result, exp_result)

    assert result["overall_score"] == round(80 * 0.5 + 100 * 0.2 + 60 * 0.3, 2)


def test_education_match_success_parses_response(monkeypatch):
    fake_text = (
        '{"score": 90, "status": "matched", "reason": "Meets requirement.", '
        '"matched": ["Bachelor\'s degree"], "missing": [], "evidence": ["BSc Computer Science"]}'
    )
    monkeypatch.setattr(matcher, "client", FakeGenAIClient(response_text=fake_text))

    result = education_match(
        {"education": [{"degree": "BSc Computer Science"}]},
        {"education_required": "Bachelor's degree"},
    )

    assert result["score"] == 90
    assert result["status"] == "matched"


def test_education_match_malformed_json_returns_error_dict(monkeypatch):
    monkeypatch.setattr(matcher, "client", FakeGenAIClient(response_text="not json"))

    result = education_match(
        {"education": [{"degree": "BSc Computer Science"}]},
        {"education_required": "Bachelor's degree"},
    )

    assert "error" in result
    assert result["raw_response"] == "not json"


def test_education_match_short_circuits_when_education_required_is_none():
    # Regression: jd.get("education_required", "").strip() crashed with
    # AttributeError when the JD parser returned {"education_required": null}
    # instead of omitting the key or using "" - the key IS present, so the
    # default never kicks in. No client call should happen here at all.
    result = education_match({"education": []}, {"education_required": None})

    assert result["score"] is None
    assert result["status"] == "not_specified"


def test_experience_match_success_parses_response(monkeypatch):
    fake_text = (
        '{"score": 85, "relevance": "High", "years_experience": 3, '
        '"matches_requirements": true, "matched": [], "missing": [], "evidence": []}'
    )
    monkeypatch.setattr(matcher, "client", FakeGenAIClient(response_text=fake_text))

    result = experience_match({"experience": []}, {"experience_required": "2 years"})

    assert result["score"] == 85
    assert result["matches_requirements"] is True


def test_experience_match_malformed_json_returns_error_dict(monkeypatch):
    monkeypatch.setattr(matcher, "client", FakeGenAIClient(response_text="not json"))

    result = experience_match({"experience": []}, {"experience_required": "2 years"})

    assert "error" in result


def test_analyze_match_success_parses_response(monkeypatch):
    fake_text = '{"overall_fit": "High", "strengths": ["Strong Python"], "weaknesses": []}'
    monkeypatch.setattr(matcher, "client", FakeGenAIClient(response_text=fake_text))

    result = analyze_match({}, {}, {})

    assert result["overall_fit"] == "High"
    assert result["strengths"] == ["Strong Python"]


def test_analyze_match_malformed_json_returns_error_dict(monkeypatch):
    monkeypatch.setattr(matcher, "client", FakeGenAIClient(response_text="not json"))

    result = analyze_match({}, {}, {})

    assert "error" in result