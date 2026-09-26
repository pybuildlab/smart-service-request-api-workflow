"""SQLite storage helpers for service requests."""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


DEFAULT_DATABASE_PATH = Path(__file__).with_name("service_requests.db")
DATABASE_PATH = Path(os.environ.get("SERVICE_REQUEST_DATABASE", DEFAULT_DATABASE_PATH))


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Open a SQLite connection and close it after the database operation."""

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()


def initialize_database() -> None:
    """Create the service request table when it does not exist yet."""

    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as connection:
        with connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS requests (
                    id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (
                        status IN ('pending', 'in_progress', 'completed', 'cancelled')
                    )
                )
                """
            )


def create_request(title: str, description: str) -> dict[str, int | str]:
    """Insert a pending request and return the stored row."""

    with get_connection() as connection:
        with connection:
            cursor = connection.execute(
                "INSERT INTO requests (title, description, status) VALUES (?, ?, ?)",
                (title, description, "pending"),
            )
            request_id = cursor.lastrowid
            row = connection.execute(
                "SELECT id, title, description, status FROM requests WHERE id = ?",
                (request_id,),
            ).fetchone()

    return dict(row)


def list_requests() -> list[dict[str, int | str]]:
    """Return all stored requests ordered by their database ID."""

    with get_connection() as connection:
        rows = connection.execute(
            "SELECT id, title, description, status FROM requests ORDER BY id"
        ).fetchall()

    return [dict(row) for row in rows]


def get_request(request_id: int) -> dict[str, int | str] | None:
    """Return one request by ID, or None when it does not exist."""

    with get_connection() as connection:
        row = connection.execute(
            "SELECT id, title, description, status FROM requests WHERE id = ?",
            (request_id,),
        ).fetchone()

    return dict(row) if row is not None else None


def update_request_status(request_id: int, request_status: str) -> dict[str, int | str] | None:
    """Update only a request status and return the stored row."""

    with get_connection() as connection:
        with connection:
            cursor = connection.execute(
                "UPDATE requests SET status = ? WHERE id = ?",
                (request_status, request_id),
            )
            if cursor.rowcount == 0:
                return None

            row = connection.execute(
                "SELECT id, title, description, status FROM requests WHERE id = ?",
                (request_id,),
            ).fetchone()

    return dict(row)
