from pathlib import Path

from backend.app.db import get_connection


def split_sql_statements(sql_text):
    return [
        statement.strip()
        for statement in sql_text.split(";")
        if statement.strip()
    ]


def main():
    schema_path = Path("backend/schema.sql")
    statements = split_sql_statements(schema_path.read_text())

    with get_connection(include_database=False) as connection:
        cursor = connection.cursor()
        for statement in statements:
            cursor.execute(statement)

    print("MySQL schema setup completed.")


if __name__ == "__main__":
    main()
