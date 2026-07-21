"""Synthetic benchmark scenarios for the ranking pipeline (Phase 4 - explainability
and evaluation, see docs/PROJECT_OBJECTIVES.md).

Each scenario is a small, hand-labeled JD + candidate batch with a known-correct
outcome. `run_evaluation.py` runs every scenario through the real deterministic
pipeline (pipeline.batch_ranker.rank_candidates, pipeline.scoring_utils) - no
Gemini calls, so this is free and repeatable - and reports pass/fail per check.

This exists to make ranking-quality claims credible rather than anecdotal: instead
of "I tried a few resumes and it looked right," this is a fixed, re-runnable set
of known-correct answers the pipeline is checked against on demand.
"""

from dataclasses import dataclass, field
from typing import Any, Callable

CheckFn = Callable[[list[dict[str, Any]]], list[str]]


@dataclass
class Scenario:
    name: str
    description: str
    jd: dict[str, Any]
    candidates: list[dict[str, Any]]
    checks: list[CheckFn] = field(default_factory=list)


def _find(ranked: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    return next((r for r in ranked if r["candidate_name"] == name), None)


def check_strong_candidate_ranks_first(ranked):
    failures = []
    top = ranked[0]
    if top["candidate_name"] != "Strong Candidate":
        failures.append(f"Expected 'Strong Candidate' to rank first, got '{top['candidate_name']}'")
    if not top["is_eligible"]:
        failures.append("Expected the top-ranked candidate to be eligible")
    return failures


def check_missing_required_skill_is_ineligible(ranked):
    candidate = _find(ranked, "Missing SQL")
    failures = []
    if candidate is None:
        return ["Candidate 'Missing SQL' not found in results"]
    if candidate["is_eligible"]:
        failures.append("Expected candidate missing a required skill to be ineligible")
    if "SQL" not in candidate["eligibility"]["missing_must_haves"]:
        failures.append("Expected 'SQL' to be listed in missing_must_haves")
    return failures


def check_insufficient_experience_is_ineligible(ranked):
    candidate = _find(ranked, "Too Junior")
    failures = []
    if candidate is None:
        return ["Candidate 'Too Junior' not found in results"]
    if candidate["is_eligible"]:
        failures.append("Expected a candidate below the minimum experience requirement to be ineligible")
    if candidate["eligibility"]["meets_experience"]:
        failures.append("Expected meets_experience to be False")
    return failures


def check_job_hopper_flagged_but_not_auto_disqualified(ranked):
    candidate = _find(ranked, "Frequent Mover")
    failures = []
    if candidate is None:
        return ["Candidate 'Frequent Mover' not found in results"]
    if candidate["job_stability"]["flag"] != "frequent_job_changes":
        failures.append(f"Expected job_stability.flag == 'frequent_job_changes', got {candidate['job_stability']}")
    # Job-hopping is a visible signal, not a hard filter (design principle 5) - this
    # candidate otherwise meets every requirement, so eligibility must be unaffected.
    if not candidate["is_eligible"]:
        failures.append("Job-hopping must not itself make an otherwise-qualified candidate ineligible")
    return failures


def check_stable_tenure_not_flagged(ranked):
    candidate = _find(ranked, "Long Tenure")
    if candidate is None:
        return ["Candidate 'Long Tenure' not found in results"]
    if candidate["job_stability"]["flag"] != "stable":
        return [f"Expected job_stability.flag == 'stable', got '{candidate['job_stability']['flag']}'"]
    return []


def check_no_education_requirement_does_not_penalize_anyone(ranked):
    failures = []
    for candidate in ranked:
        edu = candidate["match_scores"]["education"]
        if edu["score"] is not None:
            failures.append(
                f"{candidate['candidate_name']}: expected education score None when JD has no real "
                f"requirement, got {edu['score']}"
            )
        if edu["status"] != "not_specified":
            failures.append(f"{candidate['candidate_name']}: expected education status 'not_specified'")
    # Regression guard: a placeholder value like "Not specified" from the JD parser
    # must be treated the same as a genuinely empty requirement (see
    # pipeline.matcher.has_real_requirement).
    phd_candidate = _find(ranked, "PhD Holder")
    if phd_candidate and phd_candidate["education_summary"] != ["PhD from MIT (2018)"]:
        failures.append(
            "Expected the deterministic education_summary to still show the candidate's actual "
            f"degree even though the JD has no requirement, got {phd_candidate['education_summary'] if phd_candidate else None}"
        )
    return failures


def check_relative_score_floor_selects_expected_pool(ranked):
    from pipeline.scoring_utils import candidates_within_relative_floor

    failures = []
    if any(candidate["is_eligible"] for candidate in ranked):
        failures.append("This scenario is meant to have zero hard-eligible candidates")

    pool = {c["candidate_name"] for c in candidates_within_relative_floor(ranked)}
    expected_pool = {"Above Floor A", "Above Floor B"}
    if pool != expected_pool:
        failures.append(f"Expected relative-score floor pool {expected_pool}, got {pool}")
    return failures


SCENARIOS: list[Scenario] = [
    Scenario(
        name="strong_candidate_ranks_first",
        description="A candidate meeting every required skill and experience threshold should rank first and be eligible.",
        jd={
            "job_title": "Backend Engineer",
            "required_skills": ["Python", "SQL"],
            "preferred_skills": ["Docker"],
            "experience_required": "3 years",
            "education_required": "",
        },
        candidates=[
            {
                "name": "Strong Candidate",
                "normalized_skills": ["Python", "SQL", "Docker"],
                "experience": [{"job_title": "Engineer", "company": "Acme", "duration": "Jan 2019 - Jan 2023"}],
            },
            {
                "name": "Weaker Candidate",
                "normalized_skills": ["Python"],
                "experience": [{"job_title": "Engineer", "company": "Acme", "duration": "Jan 2022 - Jan 2023"}],
            },
        ],
        checks=[check_strong_candidate_ranks_first],
    ),
    Scenario(
        name="missing_required_skill_is_ineligible",
        description="A candidate missing one required skill must be marked ineligible with that skill listed as missing.",
        jd={
            "job_title": "Backend Engineer",
            "required_skills": ["Python", "SQL"],
            "preferred_skills": [],
            "experience_required": "2 years",
            "education_required": "",
        },
        candidates=[
            {
                "name": "Missing SQL",
                "normalized_skills": ["Python"],
                "experience": [{"job_title": "Engineer", "company": "Acme", "duration": "Jan 2020 - Jan 2023"}],
            },
        ],
        checks=[check_missing_required_skill_is_ineligible],
    ),
    Scenario(
        name="insufficient_experience_is_ineligible",
        description="A candidate with every required skill but below the minimum years of experience must be ineligible.",
        jd={
            "job_title": "Senior Engineer",
            "required_skills": ["Python"],
            "preferred_skills": [],
            "experience_required": "5 years",
            "education_required": "",
        },
        candidates=[
            {
                "name": "Too Junior",
                "normalized_skills": ["Python"],
                "experience": [{"job_title": "Engineer", "company": "Acme", "duration": "Jan 2022 - Jan 2023"}],
            },
        ],
        checks=[check_insufficient_experience_is_ineligible],
    ),
    Scenario(
        name="job_hopper_flagged_not_disqualified",
        description="Frequent short stints should surface as a job_stability flag without auto-rejecting an otherwise-qualified candidate.",
        jd={
            "job_title": "Backend Engineer",
            "required_skills": ["Python"],
            "preferred_skills": [],
            "experience_required": "1 year",
            "education_required": "",
        },
        candidates=[
            {
                "name": "Frequent Mover",
                "normalized_skills": ["Python"],
                "experience": [
                    {"job_title": "Engineer", "company": "A", "duration": "Jan 2020 - Jun 2020"},
                    {"job_title": "Engineer", "company": "B", "duration": "Jul 2020 - Jan 2021"},
                    {"job_title": "Engineer", "company": "C", "duration": "Feb 2021 - Sep 2021"},
                    {"job_title": "Engineer", "company": "D", "duration": "Oct 2021 - Present"},
                ],
            },
            {
                "name": "Long Tenure",
                "normalized_skills": ["Python"],
                "experience": [
                    {"job_title": "Engineer", "company": "Acme", "duration": "Jan 2015 - Jan 2023"},
                ],
            },
        ],
        checks=[check_job_hopper_flagged_but_not_auto_disqualified, check_stable_tenure_not_flagged],
    ),
    Scenario(
        name="no_education_requirement_does_not_penalize_anyone",
        description=(
            "A JD whose education_required is a JD-parser placeholder like 'Not specified' must be "
            "treated the same as a genuinely empty requirement - no candidate should be scored on it, "
            "and the deterministic education summary should still show what's actually on the resume."
        ),
        jd={
            "job_title": "AI Engineer",
            "required_skills": ["Python"],
            "preferred_skills": [],
            "experience_required": "1 year",
            "education_required": "Not specified",
        },
        candidates=[
            {
                "name": "PhD Holder",
                "normalized_skills": ["Python"],
                "experience": [{"job_title": "Engineer", "company": "Acme", "duration": "Jan 2020 - Jan 2023"}],
                "education": [{"degree": "PhD", "institution": "MIT", "year": "2018"}],
            },
            {
                "name": "No Degree Listed",
                "normalized_skills": ["Python"],
                "experience": [{"job_title": "Engineer", "company": "Acme", "duration": "Jan 2020 - Jan 2023"}],
                "education": [],
            },
        ],
        checks=[check_no_education_requirement_does_not_penalize_anyone],
    ),
    Scenario(
        name="relative_score_floor_selects_expected_pool",
        description=(
            "When nobody is hard-eligible, the relative-score fallback pool (>=50/100) should include "
            "only the candidates who actually clear that floor."
        ),
        jd={
            "job_title": "AI Engineer",
            "required_skills": ["Python", "LangGraph", "FastAPI", "Kubernetes"],
            "preferred_skills": [],
            "experience_required": "3 years",
            "education_required": "",
        },
        candidates=[
            {
                "name": "Above Floor A",
                "normalized_skills": ["Python", "LangGraph", "FastAPI"],
                "experience": [{"job_title": "Engineer", "company": "Acme", "duration": "Jan 2018 - Jan 2023"}],
            },
            {
                "name": "Above Floor B",
                "normalized_skills": ["Python", "FastAPI"],
                "experience": [{"job_title": "Engineer", "company": "Acme", "duration": "Jan 2019 - Jan 2023"}],
            },
            {
                "name": "Below Floor",
                "normalized_skills": [],
                "experience": [],
            },
        ],
        checks=[check_relative_score_floor_selects_expected_pool],
    ),
]
