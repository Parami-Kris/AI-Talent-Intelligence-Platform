import os
from contextlib import contextmanager

import mysql.connector
from dotenv import load_dotenv


load_dotenv()


def db_config(include_database=True):
    config = {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
    }

    if include_database:
        config["database"] = os.getenv("MYSQL_DATABASE", "ai_resume_screening")

    return config


@contextmanager
def get_connection(include_database=True):
    connection = mysql.connector.connect(**db_config(include_database=include_database))
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
