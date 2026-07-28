import json

from backend.app.db import get_connection


def insert_screening_run(run_name, job_title, ranking_rule, source_file, owner_id=None):
    query = """
        INSERT INTO screening_runs (run_name, job_title, ranking_rule, source_file, owner_id)
        VALUES (%s, %s, %s, %s, %s)
    """

    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(query, (run_name, job_title, ranking_rule, source_file, owner_id))
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


def _isoformat(value):
    return value.isoformat() if hasattr(value, "isoformat") else value


def list_runs_for_owner(owner_id):
    """Past screening runs ("jobs") this recruiter owns, newest first -
    powers the Shortlists list view. candidate_count only counts rows still
    marked is_shortlisted, since a recruiter may have pruned some out.
    """
    query = """
        SELECT sr.id, sr.run_name, sr.job_title, sr.source_file, sr.created_at,
               COUNT(CASE WHEN cr.is_shortlisted THEN 1 END) AS candidate_count
        FROM screening_runs sr
        LEFT JOIN candidate_rankings cr ON cr.run_id = sr.id
        WHERE sr.owner_id = %s
        GROUP BY sr.id, sr.run_name, sr.job_title, sr.source_file, sr.created_at
        ORDER BY sr.created_at DESC
    """
    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, (owner_id,))
        rows = cursor.fetchall()

    return [
        {
            "id": row["id"],
            "run_name": row["run_name"],
            "job_title": row["job_title"],
            "source_file": row["source_file"],
            "created_at": _isoformat(row["created_at"]),
            "candidate_count": row["candidate_count"],
        }
        for row in rows
    ]


def get_run_detail(run_id, owner_id):
    """Returns None if the run doesn't exist OR belongs to a different
    recruiter - both cases surface as a 404 to the caller, deliberately not
    distinguishing "not found" from "not yours" so a client can't probe for
    the existence of another recruiter's run_id.
    """
    run_query = """
        SELECT id, run_name, job_title, ranking_rule, source_file, created_at
        FROM screening_runs
        WHERE id = %s AND owner_id = %s
    """
    candidates_query = """
        SELECT cr.id AS ranking_id, cr.candidate_id, cr.is_shortlisted, cr.ranking_json
        FROM candidate_rankings cr
        WHERE cr.run_id = %s
        ORDER BY COALESCE(cr.final_rank, cr.first_pass_rank)
    """

    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(run_query, (run_id, owner_id))
        run_row = cursor.fetchone()
        if run_row is None:
            return None

        cursor.execute(candidates_query, (run_id,))
        candidate_rows = cursor.fetchall()

    candidates = [
        {
            **json.loads(row["ranking_json"]),
            "ranking_id": row["ranking_id"],
            "candidate_id": row["candidate_id"],
            "is_shortlisted": bool(row["is_shortlisted"]),
        }
        for row in candidate_rows
    ]

    return {
        "id": run_row["id"],
        "run_name": run_row["run_name"],
        "job_title": run_row["job_title"],
        "ranking_rule": run_row["ranking_rule"],
        "source_file": run_row["source_file"],
        "created_at": _isoformat(run_row["created_at"]),
        "candidates": candidates,
    }


def set_shortlisted(run_id, candidate_id, owner_id, is_shortlisted):
    """Returns False if no matching row was updated (run doesn't exist, isn't
    owned by owner_id, or candidate_id isn't part of it) - caller 404s.
    """
    query = """
        UPDATE candidate_rankings cr
        JOIN screening_runs sr ON sr.id = cr.run_id
        SET cr.is_shortlisted = %s
        WHERE cr.run_id = %s AND cr.candidate_id = %s AND sr.owner_id = %s
    """
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(query, (is_shortlisted, run_id, candidate_id, owner_id))
        return cursor.rowcount > 0
