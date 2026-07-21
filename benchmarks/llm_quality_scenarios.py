"""Hand-labeled scenarios for checking the *judgment quality* of the LLM-scored
pipeline stages - as opposed to benchmarks/scenarios.py, which only exercises the
deterministic pipeline and never calls Gemini.

Each scenario pairs a real prompt input (candidate education or experience) with
a human-labeled expected outcome bucket. `run_llm_quality_eval.py` sends these
through the real `pipeline.matcher.education_match` /
`pipeline.shortlist_reranker.rerank_experience_relevance` prompts against the
live Gemini API and reports how often the LLM's judgment agrees with the label.

Buckets are deliberately coarse (status / score range, not an exact number)
since the model isn't expected to reproduce a single "correct" score - the
question is whether it lands in the right neighborhood, not whether it matches
a human to the point.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class EducationScenario:
    name: str
    description: str
    education_required: str
    candidate_education: list[dict[str, Any]]
    expected_status: str  # "matched" | "partially_matched" | "not_matched"


@dataclass
class ExperienceScenario:
    name: str
    description: str
    jd: dict[str, Any]
    candidate_payload: dict[str, Any]
    expected_score_min: float
    expected_score_max: float


EDUCATION_SCENARIOS: list[EducationScenario] = [
    EducationScenario(
        name="exact_degree_match",
        description="Candidate holds exactly the required degree in the required field.",
        education_required="Bachelor's degree in Computer Science",
        candidate_education=[
            {"degree": "B.Sc. Computer Science", "institution": "State University", "year": "2020"}
        ],
        expected_status="matched",
    ),
    EducationScenario(
        name="higher_degree_than_required",
        description="Candidate exceeds the requirement (Master's held, Bachelor's required) in the same field.",
        education_required="Bachelor's degree in Computer Science",
        candidate_education=[
            {"degree": "M.Sc. Computer Science", "institution": "Tech Institute", "year": "2022"}
        ],
        expected_status="matched",
    ),
    EducationScenario(
        name="missing_degree_level",
        description="Candidate has no degree at all where a Bachelor's is required.",
        education_required="Bachelor's degree in Mechanical Engineering",
        candidate_education=[],
        expected_status="not_matched",
    ),
    EducationScenario(
        name="unrelated_field",
        description="Candidate holds the required degree level but in a clearly unrelated field.",
        education_required="Bachelor's degree in Electrical Engineering",
        candidate_education=[
            {"degree": "B.A. Fine Arts", "institution": "Arts College", "year": "2019"}
        ],
        expected_status="not_matched",
    ),
    EducationScenario(
        name="adjacent_field_partial_credit",
        description="Candidate's field is adjacent/related but not an exact match, which should read as partial rather than a full match or a full miss.",
        education_required="Bachelor's degree in Data Science",
        candidate_education=[
            {"degree": "B.Sc. Statistics", "institution": "State University", "year": "2021"}
        ],
        expected_status="partially_matched",
    ),
]

EXPERIENCE_SCENARIOS: list[ExperienceScenario] = [
    ExperienceScenario(
        name="highly_relevant_senior_experience",
        description="Years and domain both strongly match a senior backend role - should score high.",
        jd={
            "job_title": "Senior Backend Engineer",
            "required_skills": ["Python", "FastAPI", "PostgreSQL"],
            "responsibilities": [
                "Design and own REST APIs serving production traffic",
                "Design relational database schemas",
                "Mentor junior engineers",
            ],
            "experience_required": "5 years",
        },
        candidate_payload={
            "candidate_name": "Senior Backend Candidate",
            "first_pass_rank": 1,
            "first_pass_overall_score": 88,
            "is_eligible": True,
            "missing_must_haves": [],
            "matched_skills": ["Python", "FastAPI", "PostgreSQL"],
            "experience_years": 6,
            "experience": [
                {
                    "job_title": "Senior Backend Engineer",
                    "company": "Acme Corp",
                    "duration": "Jan 2018 - Present",
                    "description": (
                        "Designed and owned REST APIs (FastAPI) serving over 1M requests/day, "
                        "designed PostgreSQL schemas for core billing data, mentored 3 junior engineers."
                    ),
                }
            ],
            "projects": [],
        },
        expected_score_min=70,
        expected_score_max=100,
    ),
    ExperienceScenario(
        name="years_present_domain_irrelevant",
        description="Candidate has enough years but in a clearly unrelated domain (retail sales, not engineering) - relevance should score low despite meeting the years threshold.",
        jd={
            "job_title": "Machine Learning Engineer",
            "required_skills": ["Python", "PyTorch", "Model Deployment"],
            "responsibilities": [
                "Train and deploy production ML models",
                "Build model monitoring and evaluation pipelines",
            ],
            "experience_required": "4 years",
        },
        candidate_payload={
            "candidate_name": "Retail Sales Candidate",
            "first_pass_rank": 1,
            "first_pass_overall_score": 55,
            "is_eligible": True,
            "missing_must_haves": [],
            "matched_skills": ["Python"],
            "experience_years": 6,
            "experience": [
                {
                    "job_title": "Retail Store Manager",
                    "company": "Big Box Retail",
                    "duration": "Jan 2017 - Present",
                    "description": (
                        "Managed daily store operations, supervised a team of 15 sales associates, "
                        "handled inventory and scheduling using a Python-based internal reporting tool."
                    ),
                }
            ],
            "projects": [],
        },
        expected_score_min=0,
        expected_score_max=40,
    ),
    ExperienceScenario(
        name="adjacent_domain_partial_relevance",
        description="Candidate has relevant engineering experience but in an adjacent domain (data analytics, not ML engineering) - should land in the middle band, not high or low.",
        jd={
            "job_title": "Machine Learning Engineer",
            "required_skills": ["Python", "PyTorch", "Model Deployment"],
            "responsibilities": [
                "Train and deploy production ML models",
                "Build model monitoring and evaluation pipelines",
            ],
            "experience_required": "3 years",
        },
        candidate_payload={
            "candidate_name": "Data Analyst Candidate",
            "first_pass_rank": 1,
            "first_pass_overall_score": 60,
            "is_eligible": True,
            "missing_must_haves": [],
            "matched_skills": ["Python"],
            "experience_years": 4,
            "experience": [
                {
                    "job_title": "Data Analyst",
                    "company": "Acme Corp",
                    "duration": "Jan 2020 - Present",
                    "description": (
                        "Built Python data pipelines and statistical models for business reporting, "
                        "trained scikit-learn models for churn prediction, no production deployment experience."
                    ),
                }
            ],
            "projects": [],
        },
        expected_score_min=40,
        expected_score_max=69,
    ),
]
