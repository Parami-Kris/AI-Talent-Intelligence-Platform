from backend.app.db import get_connection
from pipeline.candidate_identity import normalize_email, normalize_phone


def add_comment(candidate_id, author_id, comment_text, is_caution):
    query = """
        INSERT INTO candidate_comments (candidate_id, author_id, comment_text, is_caution)
        VALUES (%s, %s, %s, %s)
    """
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(query, (candidate_id, author_id, comment_text, is_caution))
        return cursor.lastrowid


def _shape_comment_rows(rows):
    return [
        {
            "id": row["id"],
            "comment_text": row["comment_text"],
            "is_caution": bool(row["is_caution"]),
            "created_at": row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else row["created_at"],
        }
        for row in rows
    ]


def get_comments_for_candidate(candidate_id, author_id):
    """A recruiter's own past comments about a candidate - never another
    recruiter's, even though `candidates` rows are shared globally (see
    schema.sql's comment on the candidates table for why that scoping matters).
    """
    query = """
        SELECT id, comment_text, is_caution, created_at
        FROM candidate_comments
        WHERE candidate_id = %s AND author_id = %s
        ORDER BY created_at DESC
    """
    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, (candidate_id, author_id))
        return _shape_comment_rows(cursor.fetchall())


def get_comments_by_contact(emails, phones, author_id):
    """Cross-run lookup used before ranking/reranking: given the emails/phones
    parsed off the *current* batch of resumes, find this recruiter's own past
    comments on any candidate whose stored email_normalized or
    phone_normalized matches. Returns {contact_key: [comments]}, keyed by
    whichever normalized email or phone was matched, so callers can look up a
    result by either. Matches email first; a phone is only used as a fallback
    for candidates that had no email match, consistent with
    pipeline/shortlist_reranker.py's per-candidate lookup order.

    This is a deterministic SQL match, not an LLM inference step - see
    schema.sql's candidates table comment for the reliability caveat (depends
    on the candidate's contact info matching between runs).
    """
    normalized_emails = [e for e in (normalize_email(email) for email in emails) if e]
    normalized_phones = [p for p in (normalize_phone(phone) for phone in phones) if p]

    if not normalized_emails and not normalized_phones:
        return {}

    result = {}
    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)

        if normalized_emails:
            placeholders = ",".join(["%s"] * len(normalized_emails))
            query = f"""
                SELECT c.email_normalized AS contact_key, cc.id, cc.comment_text, cc.is_caution, cc.created_at
                FROM candidate_comments cc
                JOIN candidates c ON c.id = cc.candidate_id
                WHERE c.email_normalized IN ({placeholders}) AND cc.author_id = %s
                ORDER BY cc.created_at DESC
            """
            cursor.execute(query, (*normalized_emails, author_id))
            for row in cursor.fetchall():
                result.setdefault(row["contact_key"], []).append(row)

        if normalized_phones:
            placeholders = ",".join(["%s"] * len(normalized_phones))
            query = f"""
                SELECT c.phone_normalized AS contact_key, cc.id, cc.comment_text, cc.is_caution, cc.created_at
                FROM candidate_comments cc
                JOIN candidates c ON c.id = cc.candidate_id
                WHERE c.phone_normalized IN ({placeholders}) AND cc.author_id = %s
                ORDER BY cc.created_at DESC
            """
            cursor.execute(query, (*normalized_phones, author_id))
            for row in cursor.fetchall():
                result.setdefault(row["contact_key"], []).append(row)

    return {contact_key: _shape_comment_rows(rows) for contact_key, rows in result.items()}
