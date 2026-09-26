"""Additional API-level tests covering routes, error branches, and
validation boundaries not exercised by tests/test_health.py.

This module manages its own isolated SQLite database the same way
tests/test_health.py does. app.database only resolves DATABASE_PATH once
per process (at first import), so in a normal test run tests/test_health.py
is collected first and its setup wins; the setdefault() call below is a
harmless no-op in that case. Every assertion here goes through the live
database/main API rather than a hard-coded path, so this file is correct
regardless of which module happens to import app.database first.
"""

import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path


_TEMP_DIRECTORY = tempfile.TemporaryDirectory()
os.environ.setdefault(
    "SERVICE_REQUEST_DATABASE",
    str(Path(_TEMP_DIRECTORY.name) / "service_requests_test.db"),
)

from app import database, main


def tearDownModule() -> None:
    _TEMP_DIRECTORY.cleanup()


def make_request(method: str, path: str, body: dict[str, object] | None = None) -> tuple[int, object]:
    """Send a small ASGI request without an external test-client package.

    Duplicated from tests/test_health.py by design, so that file's
    existing tests and behavior remain completely untouched.
    """

    request_body = json.dumps(body).encode() if body is not None else b""
    events: list[dict[str, object]] = []
    request_received = False

    async def receive() -> dict[str, object]:
        nonlocal request_received
        if not request_received:
            request_received = True
            return {"type": "http.request", "body": request_body, "more_body": False}
        return {"type": "http.disconnect"}

    async def send(event: dict[str, object]) -> None:
        events.append(event)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [(b"content-type", b"application/json")] if body is not None else [],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
        "root_path": "",
    }

    asyncio.run(main.app(scope, receive, send))

    status_code = next(event["status"] for event in events if event["type"] == "http.response.start")
    response_body = b"".join(
        event.get("body", b"") for event in events if event["type"] == "http.response.body"
    )
    return status_code, (json.loads(response_body) if response_body else None)


def reset_requests_table() -> None:
    database.initialize_database()
    with database.get_connection() as connection:
        with connection:
            connection.execute("DELETE FROM requests")


class RootAndRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_requests_table()

    def test_root_endpoint_reports_service_is_running(self) -> None:
        status_code, response = make_request("GET", "/")

        self.assertEqual(status_code, 200)
        self.assertEqual(response["message"], "Smart Service Request API is running")
        self.assertEqual(response["version"], "0.1.0")

    def test_unsupported_method_on_requests_collection_is_rejected(self) -> None:
        status_code, _ = make_request("DELETE", "/requests")

        self.assertEqual(status_code, 405)

    def test_unsupported_method_on_single_request_is_rejected(self) -> None:
        status_code, _ = make_request("PUT", "/requests/1")

        self.assertEqual(status_code, 405)

    def test_unknown_route_returns_not_found(self) -> None:
        status_code, _ = make_request("GET", "/does-not-exist")

        self.assertEqual(status_code, 404)

    def test_get_request_with_non_integer_id_is_rejected(self) -> None:
        status_code, response = make_request("GET", "/requests/not-a-number")

        self.assertEqual(status_code, 422)
        self.assertEqual(response["detail"][0]["loc"], ["path", "request_id"])


class RequestErrorBranchTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_requests_table()

    def test_update_status_on_nonexistent_request_returns_not_found(self) -> None:
        status_code, response = make_request(
            "PATCH",
            "/requests/999/status",
            {"status": "in_progress"},
        )

        self.assertEqual(status_code, 404)
        self.assertEqual(response["detail"], "Service request with ID 999 was not found.")

    def test_update_status_with_missing_status_field_is_rejected(self) -> None:
        make_request(
            "POST",
            "/requests",
            {"title": "Monitor issue", "description": "Monitor flickers."},
        )

        status_code, response = make_request("PATCH", "/requests/1/status", {})

        self.assertEqual(status_code, 422)
        self.assertEqual(response["detail"][0]["loc"], ["body", "status"])
        self.assertEqual(response["detail"][0]["type"], "missing")

    def test_get_request_with_zero_id_returns_not_found(self) -> None:
        status_code, _ = make_request("GET", "/requests/0")

        self.assertEqual(status_code, 404)

    def test_get_request_with_negative_id_returns_not_found(self) -> None:
        status_code, _ = make_request("GET", "/requests/-1")

        self.assertEqual(status_code, 404)

    def test_list_requests_returns_empty_list_when_none_exist(self) -> None:
        status_code, response = make_request("GET", "/requests")

        self.assertEqual(status_code, 200)
        self.assertEqual(response, [])


class RequestValidationBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_requests_table()

    def test_title_at_max_length_is_accepted(self) -> None:
        status_code, response = make_request(
            "POST",
            "/requests",
            {"title": "A" * 200, "description": "Valid description."},
        )

        self.assertEqual(status_code, 201)
        self.assertEqual(len(response["title"]), 200)

    def test_title_over_max_length_is_rejected(self) -> None:
        status_code, response = make_request(
            "POST",
            "/requests",
            {"title": "A" * 201, "description": "Valid description."},
        )

        self.assertEqual(status_code, 422)
        self.assertEqual(response["detail"][0]["loc"], ["body", "title"])

    def test_description_at_max_length_is_accepted(self) -> None:
        status_code, response = make_request(
            "POST",
            "/requests",
            {"title": "Valid title", "description": "B" * 1000},
        )

        self.assertEqual(status_code, 201)
        self.assertEqual(len(response["description"]), 1000)

    def test_description_over_max_length_is_rejected(self) -> None:
        status_code, response = make_request(
            "POST",
            "/requests",
            {"title": "Valid title", "description": "B" * 1001},
        )

        self.assertEqual(status_code, 422)
        self.assertEqual(response["detail"][0]["loc"], ["body", "description"])

    def test_create_request_ignores_client_supplied_id_and_status(self) -> None:
        status_code, response = make_request(
            "POST",
            "/requests",
            {
                "title": "Badge access issue",
                "description": "Badge reader is unresponsive.",
                "id": 999,
                "status": "completed",
            },
        )

        self.assertEqual(status_code, 201)
        self.assertEqual(response["id"], 1)
        self.assertEqual(response["status"], "pending")


if __name__ == "__main__":
    unittest.main()
