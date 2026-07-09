from matcher import (
    contains_skill_text,
    eligibility_match,
    normalize_skill,
    overall_match,
    skill_match,
)


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