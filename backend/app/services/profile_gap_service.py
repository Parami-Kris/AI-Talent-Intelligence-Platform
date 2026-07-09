from typing import Any

from batch_ranker import batch_experience_match
from matcher import eligibility_match, skill_match


def analyze_profile_gap(
    jd: dict[str, Any],
    candidate: dict[str, Any],
    target_role: str | None = None,
) -> dict[str, Any]:
    skill_result = skill_match(candidate, jd)
    experience_result = batch_experience_match(candidate, jd)
    eligibility = eligibility_match(skill_result, experience_result)

    missing_must_haves = eligibility.get("missing_must_haves", [])
    missing_experience = experience_result.get("missing", [])
    matched_skills = skill_result.get("matched", [])

    if not missing_must_haves and not missing_experience:
        current_fit = "strong"
    elif len(missing_must_haves) <= 5 and experience_result.get("matches_requirements"):
        current_fit = "partial"
    else:
        current_fit = "weak"

    suggested_projects = [
        f"Build a project that demonstrates {skill} in the context of {target_role or jd.get('job_title', 'the target role')}."
        for skill in missing_must_haves[:5]
    ]

    resume_recommendations = [
        f"Add evidence for {skill} if you have used it in projects, internships, or coursework."
        for skill in missing_must_haves[:5]
    ]

    if missing_experience:
        resume_recommendations.append(
            "Add clear dates, role ownership, and domain-specific responsibilities to strengthen experience evidence."
        )

    return {
        "target_role": target_role or jd.get("job_title"),
        "candidate_name": candidate.get("name", "Unknown Candidate"),
        "current_fit": current_fit,
        "role_readiness_score": skill_result.get("score", 0),
        "eligibility": eligibility,
        "qualification_gaps": {
            "missing_required_skills": missing_must_haves,
            "missing_experience_signals": missing_experience,
            "matched_skills": matched_skills,
        },
        "recommended_actions": {
            "suggested_projects": suggested_projects,
            "resume_improvements": resume_recommendations,
            "learning_focus": missing_must_haves[:8],
        },
        "evidence": {
            "skills": skill_result.get("evidence", []),
            "experience": experience_result.get("evidence", []),
        },
    }
