import json
from typing import Any

from backend.app.db import get_connection


def save_pending_review(
    thread_id: str,
    jd: dict[str, Any],
    candidates: list[dict[str, Any]],
    batch_ranking: dict[str, Any],
    reranked: dict[str, Any],
    run_name: str,
    source_file: str,
    top_n: int,
) -> None:
    query = """
        INSERT INTO pipeline_reviews (
            thread_id, jd, candidates, batch_ranking, reranked,
            run_name, source_file, top_n, status
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'awaiting_review')
    """
    values = (
        thread_id,
        json.dumps(jd),
        json.dumps(candidates),
        json.dumps(batch_ranking),
        json.dumps(reranked),
        run_name,
        source_file,
        top_n,
    )

    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(query, values)


def get_pending_review(thread_id: str) -> dict[str, Any] | None:
    query = """
        SELECT thread_id, jd, candidates, batch_ranking, reranked,
               run_name, source_file, top_n, status
        FROM pipeline_reviews
        WHERE thread_id = %s
    """

    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, (thread_id,))
        row = cursor.fetchone()

    if row is None:
        return None

    return {
        "thread_id": row["thread_id"],
        "jd": json.loads(row["jd"]),
        "candidates": json.loads(row["candidates"]),
        "batch_ranking": json.loads(row["batch_ranking"]),
        "reranked": json.loads(row["reranked"]),
        "run_name": row["run_name"],
        "source_file": row["source_file"],
        "top_n": row["top_n"],
        "status": row["status"],
    }


def mark_review_resolved(thread_id: str, status: str) -> None:
    query = """
        UPDATE pipeline_reviews
        SET status = %s, resolved_at = CURRENT_TIMESTAMP
        WHERE thread_id = %s
    """

    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(query, (status, thread_id))
