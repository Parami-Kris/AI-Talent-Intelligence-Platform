import argparse
import json
from pathlib import Path

from backend.app.ranking_repository import (
    insert_candidate_ranking,
    insert_score_evidence,
    insert_screening_run,
    upsert_candidate,
)


def load_rankings(path):
    with open(path, "r") as f:
        return json.load(f)


def collect_evidence(result):
    match_scores = result.get("match_scores", {})
    evidence = {
        "skills": match_scores.get("skills", {}).get("evidence", []),
        "experience_years": match_scores.get("experience", {}).get("evidence", []),
        "education": match_scores.get("education", {}).get("evidence", []),
    }

    relevance = result.get("experience_relevance")
    if relevance:
        evidence["experience_relevance"] = relevance.get("evidence", [])

    return evidence


def save_rankings(path, run_name):
    payload = load_rankings(path)
    run_id = insert_screening_run(
        run_name=run_name,
        job_title=payload.get("job_title"),
        ranking_rule=payload.get("ranking_rule"),
        source_file=str(Path(path).name),
    )

    for result in payload.get("results", []):
        candidate_id = upsert_candidate(
            name=result.get("candidate_name", "Unknown Candidate"),
            email=result.get("email"),
        )
        ranking_id = insert_candidate_ranking(run_id, candidate_id, result)

        for score_type, evidence_items in collect_evidence(result).items():
            insert_score_evidence(ranking_id, score_type, evidence_items)

    return run_id


def main():
    parser = argparse.ArgumentParser(description="Save ranking results into MySQL.")
    parser.add_argument("--input", default="final_rankings.json")
    parser.add_argument("--run-name", default="Synthetic senior AI/ML screening run")
    args = parser.parse_args()

    run_id = save_rankings(args.input, args.run_name)
    print(f"Saved rankings to MySQL with run_id={run_id}")


if __name__ == "__main__":
    main()
