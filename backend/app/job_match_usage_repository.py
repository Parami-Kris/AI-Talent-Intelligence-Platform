from datetime import date

from backend.app.db import get_connection


def get_today_usage(user_id):
    query = "SELECT jobs_scored FROM job_match_usage WHERE user_id = %s AND usage_date = %s"
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(query, (user_id, date.today()))
        row = cursor.fetchone()
    return row[0] if row else 0


def increment_usage(user_id, count):
    if count <= 0:
        return

    query = """
        INSERT INTO job_match_usage (user_id, usage_date, jobs_scored)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE jobs_scored = jobs_scored + VALUES(jobs_scored)
    """
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(query, (user_id, date.today(), count))
