from backend.app.db import get_connection


def create_user(email, password_hash, role, display_name=None):
    query = """
        INSERT INTO users (email, password_hash, role, display_name)
        VALUES (%s, %s, %s, %s)
    """
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(query, (email, password_hash, role, display_name))
        return cursor.lastrowid


def get_user_by_email(email):
    query = "SELECT id, email, password_hash, role, display_name FROM users WHERE email = %s"
    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, (email,))
        return cursor.fetchone()


def get_user_by_id(user_id):
    query = "SELECT id, email, password_hash, role, display_name FROM users WHERE id = %s"
    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, (user_id,))
        return cursor.fetchone()
