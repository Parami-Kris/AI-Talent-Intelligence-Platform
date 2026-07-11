import json

from backend.app.db import get_connection


def get_cached_expansion(normalized_query: str) -> list[str] | None:
    query = "SELECT related_titles FROM query_expansions WHERE query_text = %s"

    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(query, (normalized_query,))
        row = cursor.fetchone()

    if row is None:
        return None

    return json.loads(row[0])


def save_expansion(normalized_query: str, related_titles: list[str]) -> None:
    query = """
        INSERT INTO query_expansions (query_text, related_titles)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE related_titles = VALUES(related_titles)
    """

    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(query, (normalized_query, json.dumps(related_titles)))
