import argparse
import json
import logging
import re
from datetime import date

from pipeline.matcher import (
    MODEL_ID,
    client,
    eligibility_match,
    jd_data,
    overall_match,
    skill_match,
)

from backend.app.utils.llm_json import parse_llm_json

logger = logging.getLogger(__name__)


MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


def parse_month_year(value):
    value = value.strip().lower()
    if value in {"current", "present", "now"}:
        today = date.today()
        return date(today.year, today.month, 1)

    match = re.search(r"([a-z]+)\s+(\d{4})", value)
    if match:
        month = MONTHS.get(match.group(1))
        if month:
            return date(int(match.group(2)), month, 1)

    year_match = re.search(r"\d{4}", value)
    if year_match:
        return date(int(year_match.group()), 1, 1)

    return None


def duration_years(duration):
    if not duration:
        return 0

    parts = re.split(r"\s*(?:-|–|to)\s*", duration, maxsplit=1, flags=re.IGNORECASE)
    start = parse_month_year(parts[0])
    end = parse_month_year(parts[1]) if len(parts) > 1 else start

    if not start or not end or end < start:
        return 0

    months = (end.year - start.year) * 12 + (end.month - start.month) + 1
    return max(months / 12, 0)


def minimum_required_years(experience_required):
    match = re.search(r"(\d+(?:\.\d+)?)", experience_required or "")
    return float(match.group(1)) if match else 0


def batch_experience_match(candidate, jd):
    min_years = minimum_required_years(jd.get("experience_required", ""))
    evidence = []
    total_years = 0

    for item in candidate.get("experience", []):
        years = duration_years(item.get("duration", ""))
        total_years += years
        title = item.get("job_title", "Experience")
        company = item.get("company", "").strip()
        label = f"{title} at {company}" if company else title
        evidence.append(f"{label}: {item.get('duration', 'duration not specified')} ({round(years, 2)} years)")

    meets_requirement = total_years >= min_years if min_years else True
    score = 100 if meets_requirement else round((total_years / min_years) * 100, 2) if min_years else 100

    return {
        "score": min(score, 100),
        "relevance": "Not evaluated in deterministic batch mode",
        "years_experience": round(total_years, 2),
        "matches_requirements": meets_requirement,
        "matched": [f"Meets minimum experience requirement of {min_years:g} years"] if meets_requirement and min_years else [],
        "missing": [] if meets_requirement else [f"Minimum experience requirement of {min_years:g} years"],
        "evidence": evidence + [f"Total calculated experience: {round(total_years, 2)} years"],
    }


def default_education_result(reason):
    return {
        "score": None,
        "status": "not_specified",
        "reason": reason,
        "matched": [],
        "missing": [],
        "evidence": [reason],
    }


def batch_education_match(candidates, jd):
    jd_edu = (jd.get("education_required") or "").strip()
    if not jd_edu:
        return [
            default_education_result("The job description does not specify an education requirement.")
            for _ in candidates
        ]

    education_payload = [
        {
            "candidate_index": index,
            "candidate_name": candidate.get("name", "Unknown Candidate"),
            "education": candidate.get("education", []),
            "certifications": candidate.get("certifications", []),
        }
        for index, candidate in enumerate(candidates)
    ]

    prompt = f"""
You are evaluating multiple candidates' education against one job requirement.

Job education requirement:
{jd_edu}

Candidates:
{json.dumps(education_payload, indent=2)}

Return ONLY valid JSON as a list. Return one result per candidate, preserving candidate_index.

[
  {{
    "candidate_index": 0,
    "candidate_name": "Candidate Name",
    "score": X,
    "status": "matched|partially_matched|not_matched",
    "reason": "Short evidence-based explanation",
    "matched": ["Education requirements the candidate meets"],
    "missing": ["Education requirements the candidate does not meet"],
    "evidence": ["Specific degree, institution, certification, or resume fact"]
  }}
]
"""
    response = client.models.generate_content(model=MODEL_ID, contents=prompt)
    raw = parse_llm_json(response.text)

    if isinstance(raw, dict) and "error" in raw:
        logger.error("Batch education match failed to parse LLM response: %s", raw["error"])
        return [
            default_education_result(
                "Education evaluation could not be completed due to a parsing error; treated as not evaluated."
            )
            for _ in candidates
        ]

    results = raw if isinstance(raw, list) else []

    by_index = {
        item.get("candidate_index"): item
        for item in results
        if isinstance(item.get("candidate_index"), int)
    }

    return [
        by_index.get(
            index,
            {
                "score": 0,
                "status": "not_matched",
                "reason": "Education result missing from batch LLM response.",
                "matched": [],
                "missing": [jd_edu],
                "evidence": [],
            },
        )
        for index in range(len(candidates))
    ]


def rank_candidate(candidate, jd, edu_result):
    skill_result = skill_match(candidate, jd)
    exp_result = batch_experience_match(candidate, jd)
    overall_result = overall_match(skill_result, edu_result, exp_result)
    eligibility = eligibility_match(skill_result, exp_result)
    is_eligible = (
        eligibility.get("meets_experience", False)
        and len(eligibility.get("missing_must_haves", [])) == 0
    )

    return {
        "candidate_name": candidate.get("name", "Unknown Candidate"),
        "email": candidate.get("email"),
        "eligibility": eligibility,
        "is_eligible": is_eligible,
        "overall_score": overall_result["overall_score"],
        "match_scores": {
            "skills": skill_result,
            "experience": exp_result,
            "education": edu_result,
        },
    }


def ranking_key(result):
    return (
        result["is_eligible"],
        result["overall_score"],
        result["match_scores"]["skills"]["score"],
    )


def rank_candidates(candidates, jd):
    education_results = batch_education_match(candidates, jd)
    ranked = [
        rank_candidate(candidate, jd, education_results[index])
        for index, candidate in enumerate(candidates)
    ]
    ranked.sort(key=ranking_key, reverse=True)

    for index, result in enumerate(ranked, start=1):
        result["rank"] = index

    return ranked


def build_summary(ranked):
    return [
        {
            "rank": result["rank"],
            "candidate_name": result["candidate_name"],
            "is_eligible": result["is_eligible"],
            "overall_score": result["overall_score"],
            "skill_score": result["match_scores"]["skills"]["score"],
            "experience_score": result["match_scores"]["experience"]["score"],
            "meets_experience": result["eligibility"]["meets_experience"],
            "missing_must_haves_count": len(result["eligibility"]["missing_must_haves"]),
            "top_missing_must_haves": result["eligibility"]["missing_must_haves"][:5],
        }
        for result in ranked
    ]


def main():
    parser = argparse.ArgumentParser(description="Rank multiple parsed candidate profiles against the parsed JD.")
    parser.add_argument("--candidates", default="synthetic_candidates.json")
    parser.add_argument("--output", default="batch_rankings.json")
    args = parser.parse_args()

    with open(args.candidates, "r") as f:
        candidates = json.load(f)

    ranked = rank_candidates(candidates, jd_data)
    output = {
        "job_title": jd_data.get("job_title"),
        "ranking_rule": "Eligible candidates first, then overall_score, then skill_score.",
        "summary": build_summary(ranked),
        "results": ranked,
    }

    with open(args.output, "w") as f:
        json.dump(output, f, indent=4)

    print(json.dumps(output["summary"], indent=4))


if __name__ == "__main__":
    main()
