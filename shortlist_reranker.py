import argparse
import json

from matcher import MODEL_ID, client, jd_data


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def candidate_lookup(candidates):
    return {
        candidate.get("name", ""): candidate
        for candidate in candidates
    }


def build_shortlist_payload(first_pass_results, candidates_by_name, top_n):
    shortlisted = first_pass_results[:top_n]
    payload = []

    for item in shortlisted:
        candidate = candidates_by_name.get(item["candidate_name"], {})
        payload.append(
            {
                "candidate_name": item["candidate_name"],
                "first_pass_rank": item["rank"],
                "first_pass_overall_score": item["overall_score"],
                "is_eligible": item["is_eligible"],
                "missing_must_haves": item["eligibility"]["missing_must_haves"],
                "matched_skills": item["match_scores"]["skills"]["matched"],
                "experience_years": item["match_scores"]["experience"]["years_experience"],
                "experience": candidate.get("experience", []),
                "projects": candidate.get("projects", []),
            }
        )

    return payload


def rerank_experience_relevance(shortlist_payload, jd):
    prompt = f"""
You are reranking shortlisted candidates for experience relevance.

This is a second-stage review after cheap batch filtering.
The first-pass experience years check only verifies duration. Your job is to judge whether the candidate's actual work is relevant to this JD.

Job title:
{jd.get("job_title")}

Required skills:
{json.dumps(jd.get("required_skills", []), indent=2)}

Responsibilities:
{json.dumps(jd.get("responsibilities", []), indent=2)}

Experience requirement:
{jd.get("experience_required", "")}

Shortlisted candidates:
{json.dumps(shortlist_payload, indent=2)}

Scoring guidance:
- 90-100: highly relevant senior experience matching the JD responsibilities.
- 70-89: relevant experience, but some gaps.
- 40-69: adjacent experience with meaningful gaps.
- 0-39: years may exist, but domain/responsibility relevance is weak.

Return ONLY valid JSON as a list, one result per candidate:

[
  {{
    "candidate_name": "Candidate Name",
    "experience_relevance_score": 0,
    "seniority_fit": "strong|partial|weak",
    "domain_fit": "strong|partial|weak",
    "reason": "Short evidence-based explanation",
    "matched": ["Relevant experience signals"],
    "missing": ["Relevant JD experience gaps"],
    "evidence": ["Specific role, duration, responsibility, or project"]
  }}
]
"""
    response = client.models.generate_content(model=MODEL_ID, contents=prompt)
    cleaned = response.text.replace("```json", "").replace("```", "").strip()
    return json.loads(cleaned)


def merge_rerank_results(first_pass, rerank_results):
    by_name = {
        item["candidate_name"]: item
        for item in rerank_results
    }

    final_results = []
    for result in first_pass:
        relevance = by_name.get(result["candidate_name"])
        final_score = result["overall_score"]

        if relevance:
            final_score = round(
                (result["overall_score"] * 0.6)
                + (relevance["experience_relevance_score"] * 0.4),
                2,
            )

        enriched = {
            **result,
            "experience_relevance": relevance,
            "final_score": final_score,
        }
        final_results.append(enriched)

    final_results.sort(
        key=lambda item: (
            item["is_eligible"],
            item["final_score"],
            item["overall_score"],
        ),
        reverse=True,
    )

    for index, item in enumerate(final_results, start=1):
        item["final_rank"] = index

    return final_results


def build_summary(final_results):
    return [
        {
            "final_rank": item["final_rank"],
            "candidate_name": item["candidate_name"],
            "is_eligible": item["is_eligible"],
            "final_score": item["final_score"],
            "first_pass_rank": item["rank"],
            "first_pass_overall_score": item["overall_score"],
            "experience_relevance_score": (
                item["experience_relevance"]["experience_relevance_score"]
                if item["experience_relevance"]
                else None
            ),
            "seniority_fit": (
                item["experience_relevance"]["seniority_fit"]
                if item["experience_relevance"]
                else None
            ),
            "domain_fit": (
                item["experience_relevance"]["domain_fit"]
                if item["experience_relevance"]
                else None
            ),
        }
        for item in final_results
    ]


def main():
    parser = argparse.ArgumentParser(description="LLM rerank shortlisted candidates for experience relevance.")
    parser.add_argument("--batch-rankings", default="batch_rankings.json")
    parser.add_argument("--candidates", default="synthetic_candidates.json")
    parser.add_argument("--output", default="final_rankings.json")
    parser.add_argument("--top-n", type=int, default=10)
    args = parser.parse_args()

    batch_rankings = load_json(args.batch_rankings)
    candidates = load_json(args.candidates)
    candidates_by_name = candidate_lookup(candidates)

    first_pass_results = batch_rankings["results"]
    shortlist_payload = build_shortlist_payload(first_pass_results, candidates_by_name, args.top_n)
    rerank_results = rerank_experience_relevance(shortlist_payload, jd_data)
    final_results = merge_rerank_results(first_pass_results, rerank_results)

    output = {
        "job_title": jd_data.get("job_title"),
        "ranking_rule": "Eligible candidates first, then final_score. final_score = 60% first-pass overall + 40% LLM experience relevance for shortlisted candidates.",
        "shortlist_size": len(shortlist_payload),
        "summary": build_summary(final_results),
        "results": final_results,
    }

    with open(args.output, "w") as f:
        json.dump(output, f, indent=4)

    print(json.dumps(output["summary"], indent=4))


if __name__ == "__main__":
    main()
