"""Tests for the Batch 12 dynamic website frame: static asset serving, and
its integration with the existing JSON API.

This does not execute JavaScript (no browser is available in this test
environment) - it verifies the frontend is served correctly, and that the
exact HTTP contract app.js relies on (status codes, JSON response shapes,
error-body shapes) behaves the way the frontend code expects. See
app/static/js/app.js for the client-side logic that consumes these routes.
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


def reset_requests_table() -> None:
    database.initialize_database()
    with database.get_connection() as connection:
        with connection:
            connection.execute("DELETE FROM requests")


def make_request(method: str, path: str, body: dict[str, object] | None = None, as_json: bool = True):
    """Send a small ASGI request without an external test-client package.

    Duplicated from the pattern used in tests/test_health.py and
    tests/test_requests_api.py by design, so those files remain untouched.
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
    response_headers = dict(
        next(event["headers"] for event in events if event["type"] == "http.response.start")
    )
    response_body = b"".join(
        event.get("body", b"") for event in events if event["type"] == "http.response.body"
    )
    parsed = json.loads(response_body) if (as_json and response_body) else response_body
    return status_code, parsed, response_headers


class StaticAssetTests(unittest.TestCase):
    def test_dashboard_route_serves_html(self) -> None:
        status_code, body, headers = make_request("GET", "/app", as_json=False)

        self.assertEqual(status_code, 200)
        self.assertIn(b"text/html", headers[b"content-type"])
        self.assertIn(b"<title>Smart Service Request Dashboard</title>", body)
        self.assertIn(b'id="request-form"', body)
        self.assertIn(b'id="request-list"', body)
        self.assertIn(b'src="/static/js/app.js"', body)
        self.assertIn(b'href="/static/css/style.css"', body)

    def test_stylesheet_is_served(self) -> None:
        status_code, body, headers = make_request("GET", "/static/css/style.css", as_json=False)

        self.assertEqual(status_code, 200)
        self.assertIn(b"text/css", headers[b"content-type"])
        self.assertGreater(len(body), 0)

    def test_javascript_is_served(self) -> None:
        status_code, body, headers = make_request("GET", "/static/js/app.js", as_json=False)

        self.assertEqual(status_code, 200)
        self.assertGreater(len(body), 0)
        self.assertIn(b"fetch(", body)
        self.assertIn(b"/requests", body)

    def test_dashboard_route_is_excluded_from_openapi_schema(self) -> None:
        schema = main.app.openapi()

        self.assertNotIn("/app", schema["paths"])

    def test_unknown_static_asset_returns_not_found(self) -> None:
        status_code, _, _ = make_request("GET", "/static/does-not-exist.js", as_json=False)

        self.assertEqual(status_code, 404)

    def test_existing_api_routes_are_unaffected_by_the_new_static_mount(self) -> None:
        status_code, response, _ = make_request("GET", "/")

        self.assertEqual(status_code, 200)
        self.assertEqual(response["message"], "Smart Service Request API is running")
        self.assertEqual(response["version"], "0.1.0")


class DashboardWorkflowIntegrationTests(unittest.TestCase):
    """Exercises the exact create/list/update sequence and response shapes
    that app.js drives via fetch()."""

    def setUp(self) -> None:
        reset_requests_table()

    def test_full_create_list_update_workflow_matches_frontend_expectations(self) -> None:
        create_status, created, _ = make_request(
            "POST",
            "/requests",
            {"title": "Printer offline", "description": "Second floor printer is offline."},
        )
        self.assertEqual(create_status, 201)
        self.assertEqual(created["status"], "pending")
        self.assertIn("id", created)

        list_status, requests, _ = make_request("GET", "/requests")
        self.assertEqual(list_status, 200)
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0]["id"], created["id"])

        update_status_code, updated, _ = make_request(
            "PATCH",
            f"/requests/{created['id']}/status",
            {"status": "in_progress"},
        )
        self.assertEqual(update_status_code, 200)
        self.assertEqual(updated["status"], "in_progress")

    def test_create_validation_error_shape_matches_what_the_frontend_parses(self) -> None:
        # app.js reads body.detail as a list of {loc, msg} for 422s.
        status_code, response, _ = make_request(
            "POST",
            "/requests",
            {"title": "", "description": "Valid description."},
        )

        self.assertEqual(status_code, 422)
        self.assertIsInstance(response["detail"], list)
        self.assertIn("loc", response["detail"][0])
        self.assertIn("msg", response["detail"][0])

    def test_not_found_error_shape_matches_what_the_frontend_parses(self) -> None:
        # app.js reads body.detail as a plain string for 404s.
        status_code, response, _ = make_request(
            "PATCH",
            "/requests/999999/status",
            {"status": "completed"},
        )

        self.assertEqual(status_code, 404)
        self.assertIsInstance(response["detail"], str)


if __name__ == "__main__":
    unittest.main()
