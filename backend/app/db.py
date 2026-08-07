import os
from contextlib import contextmanager

import mysql.connector
from dotenv import load_dotenv
from mysql.connector.pooling import MySQLConnectionPool


load_dotenv()

_pool: MySQLConnectionPool | None = None


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


def _get_pool() -> MySQLConnectionPool:
    # Every request-time caller connects with include_database=True (the
    # setup_mysql.py script is the only include_database=False caller, and it
    # calls db_config directly rather than going through this pool), so one
    # pool keyed on that config is enough - a fresh TLS handshake to TiDB per
    # request was the actual cause of ~3s+ added latency on every DB-touching
    # endpoint.
    global _pool
    if _pool is None:
        _pool = MySQLConnectionPool(pool_name="app_pool", pool_size=5, **db_config(include_database=True))
    return _pool


@contextmanager
def get_connection(include_database=True):
    connection = _get_pool().get_connection() if include_database else mysql.connector.connect(
        **db_config(include_database=False)
    )
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
