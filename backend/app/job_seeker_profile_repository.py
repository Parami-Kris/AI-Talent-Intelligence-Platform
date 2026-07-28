import json

from backend.app.db import get_connection


def get_resume(user_id):
    query = "SELECT resume_filename, parsed_resume, updated_at FROM job_seeker_profiles WHERE user_id = %s"
    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, (user_id,))
        row = cursor.fetchone()

    if row is None:
        return None

    return {
        "resume_filename": row["resume_filename"],
        "parsed_resume": json.loads(row["parsed_resume"]),
        "updated_at": row["updated_at"].isoformat() if hasattr(row["updated_at"], "isoformat") else row["updated_at"],
    }


def save_resume(user_id, resume_filename, parsed_resume):
    query = """
        INSERT INTO job_seeker_profiles (user_id, resume_filename, parsed_resume)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE resume_filename = VALUES(resume_filename), parsed_resume = VALUES(parsed_resume)
    """
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(query, (user_id, resume_filename, json.dumps(parsed_resume)))
