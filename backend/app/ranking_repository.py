import json

from backend.app.db import get_connection


def insert_screening_run(run_name, job_title, ranking_rule, source_file):
    query = """
        INSERT INTO screening_runs (run_name, job_title, ranking_rule, source_file)
        VALUES (%s, %s, %s, %s)
    """

    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(query, (run_name, job_title, ranking_rule, source_file))
        return cursor.lastrowid


def upsert_candidate(name, email):
    select_query = "SELECT id FROM candidates WHERE email = %s"
    insert_query = "INSERT INTO candidates (name, email) VALUES (%s, %s)"

    with get_connection() as connection:
        cursor = connection.cursor()

        if email:
            cursor.execute(select_query, (email,))
            row = cursor.fetchone()
            if row:
                return row[0]

        cursor.execute(insert_query, (name, email))
        return cursor.lastrowid


def insert_candidate_ranking(run_id, candidate_id, ranking):
    skills = ranking.get("match_scores", {}).get("skills", {})
    experience = ranking.get("match_scores", {}).get("experience", {})
    eligibility = ranking.get("eligibility", {})
    relevance = ranking.get("experience_relevance") or {}

    query = """
        INSERT INTO candidate_rankings (
            run_id,
            candidate_id,
            first_pass_rank,
            final_rank,
            is_eligible,
            first_pass_overall_score,
            final_score,
            skill_score,
            experience_years_score,
            experience_relevance_score,
            seniority_fit,
            domain_fit,
            missing_must_haves_count,
            ranking_json
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    values = (
        run_id,
        candidate_id,
        ranking.get("rank"),
        ranking.get("final_rank"),
        ranking.get("is_eligible"),
        ranking.get("overall_score"),
        ranking.get("final_score"),
        skills.get("score"),
        experience.get("score"),
        relevance.get("experience_relevance_score"),
        relevance.get("seniority_fit"),
        relevance.get("domain_fit"),
        len(eligibility.get("missing_must_haves", [])),
        json.dumps(ranking),
    )

    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(query, values)
        return cursor.lastrowid


def insert_score_evidence(ranking_id, score_type, evidence_items):
    if not evidence_items:
        return

    query = """
        INSERT INTO score_evidence (ranking_id, score_type, evidence_text)
        VALUES (%s, %s, %s)
    """
    values = [
        (ranking_id, score_type, evidence)
        for evidence in evidence_items
    ]

    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.executemany(query, values)
