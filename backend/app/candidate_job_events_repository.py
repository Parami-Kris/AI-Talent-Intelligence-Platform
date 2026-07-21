from backend.app.db import get_connection

# 'searched' events intentionally excluded - they carry a free-text query, not a
# job_title, so get_recommended_query's title-based aggregation never sees them
# anyway. Weighted so an explicit "like" counts for more than an inferred "applied"
# click, which counts for more than passively viewing a result.
EVENT_WEIGHTS = {"liked": 3, "applied": 2, "viewed": 1}


def log_event(
    candidate_id,
    event_type,
    *,
    query_text=None,
    job_source=None,
    job_external_id=None,
    job_title=None,
    company=None,
    location=None,
):
    query = """
        INSERT INTO candidate_job_events
            (candidate_id, event_type, query_text, job_source, job_external_id, job_title, company, location)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            query,
            (candidate_id, event_type, query_text, job_source, job_external_id, job_title, company, location),
        )


def pick_best_title(rows):
    """Pure scoring step, split out from get_recommended_query so it's testable
    without a real DB connection. `rows` is (job_title, event_type, event_count)
    tuples, as returned by the GROUP BY query below.
    """
    scores = {}
    for job_title, event_type, event_count in rows:
        weight = EVENT_WEIGHTS.get(event_type, 0)
        if weight == 0:
            continue
        scores[job_title] = scores.get(job_title, 0) + weight * event_count

    if not scores:
        return None

    return max(scores, key=scores.get)


def get_recommended_query(candidate_id):
    """Best-guess search query for a candidate who searched with no keyword,
    based on weighted (liked > applied > viewed) past job-title interactions.
    Returns None if there's no usable history yet.
    """
    query = """
        SELECT job_title, event_type, COUNT(*) AS event_count
        FROM candidate_job_events
        WHERE candidate_id = %s AND job_title IS NOT NULL AND job_title != ''
        GROUP BY job_title, event_type
    """
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(query, (candidate_id,))
        rows = cursor.fetchall()

    return pick_best_title(rows)
