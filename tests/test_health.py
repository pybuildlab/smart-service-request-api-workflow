import asyncio
import json
import unittest

from app import main


def make_request(method: str, path: str, body: dict[str, str] | None = None) -> tuple[int, object]:
    """Send a small ASGI request without an external test-client package."""

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
        "headers": [(b"content-type", b"application/json")] if body else [],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
        "root_path": "",
    }

    asyncio.run(main.app(scope, receive, send))

    status_code = next(event["status"] for event in events if event["type"] == "http.response.start")
    response_body = b"".join(
        event.get("body", b"") for event in events if event["type"] == "http.response.body"
    )
    return status_code, json.loads(response_body)


class ServiceRequestApiTests(unittest.TestCase):
    def setUp(self) -> None:
        main.service_requests.clear()
        main.next_request_id = 1

    def test_create_request(self) -> None:
        status_code, response = make_request(
            "POST",
            "/requests",
            {
                "title": "Internet connection issue",
                "description": "The office internet is unavailable.",
            },
        )

        self.assertEqual(status_code, 201)
        self.assertEqual(
            response,
            {
                "id": 1,
                "title": "Internet connection issue",
                "description": "The office internet is unavailable.",
                "status": "pending",
            },
        )

    def test_list_requests(self) -> None:
        make_request(
            "POST",
            "/requests",
            {"title": "Printer issue", "description": "The printer is offline."},
        )

        status_code, response = make_request("GET", "/requests")

        self.assertEqual(status_code, 200)
        self.assertEqual(len(response), 1)
        self.assertEqual(response[0]["title"], "Printer issue")

    def test_get_existing_request(self) -> None:
        make_request(
            "POST",
            "/requests",
            {"title": "Email issue", "description": "Email cannot send messages."},
        )
        make_request(
            "POST",
            "/requests",
            {"title": "Network issue", "description": "The network is slow."},
        )

        status_code, response = make_request("GET", "/requests/2")

        self.assertEqual(status_code, 200)
        self.assertEqual(
            response,
            {
                "id": 2,
                "title": "Network issue",
                "description": "The network is slow.",
                "status": "pending",
            },
        )

    def test_get_nonexistent_request_returns_not_found(self) -> None:
        status_code, response = make_request("GET", "/requests/999")

        self.assertEqual(status_code, 404)
        self.assertEqual(response["detail"], "Service request with ID 999 was not found.")

    def test_update_request_status(self) -> None:
        make_request(
            "POST",
            "/requests",
            {"title": "Laptop issue", "description": "Laptop will not start."},
        )

        status_code, response = make_request(
            "PATCH",
            "/requests/1/status",
            {"status": "in_progress"},
        )

        self.assertEqual(status_code, 200)
        self.assertEqual(
            response,
            {
                "id": 1,
                "title": "Laptop issue",
                "description": "Laptop will not start.",
                "status": "in_progress",
            },
        )

    def test_updated_status_is_returned_by_request_endpoints(self) -> None:
        make_request(
            "POST",
            "/requests",
            {"title": "First issue", "description": "The first request."},
        )
        make_request(
            "POST",
            "/requests",
            {"title": "Second issue", "description": "The second request."},
        )
        make_request(
            "PATCH",
            "/requests/2/status",
            {"status": "completed"},
        )

        single_status_code, single_response = make_request("GET", "/requests/2")
        list_status_code, list_response = make_request("GET", "/requests")

        self.assertEqual(single_status_code, 200)
        self.assertEqual(
            single_response,
            {
                "id": 2,
                "title": "Second issue",
                "description": "The second request.",
                "status": "completed",
            },
        )
        self.assertEqual(list_status_code, 200)
        self.assertEqual([request["id"] for request in list_response], [1, 2])
        self.assertEqual([request["status"] for request in list_response], ["pending", "completed"])

    def test_invalid_status_is_rejected(self) -> None:
        make_request(
            "POST",
            "/requests",
            {"title": "Keyboard issue", "description": "Keyboard keys are stuck."},
        )

        status_code, response = make_request(
            "PATCH",
            "/requests/1/status",
            {"status": "unknown"},
        )

        self.assertEqual(status_code, 422)
        self.assertEqual(response["detail"][0]["loc"], ["body", "status"])
        self.assertEqual(response["detail"][0]["type"], "literal_error")

    def test_invalid_request_payload_is_rejected(self) -> None:
        invalid_payloads = [
            {"title": "", "description": "A valid description."},
            {"title": "   ", "description": "A valid description."},
            {"title": "Valid title"},
            {"title": "Valid title", "description": "   "},
        ]

        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                status_code, response = make_request("POST", "/requests", payload)

                self.assertEqual(status_code, 422)
                self.assertTrue(response["detail"])
                self.assertEqual(response["detail"][0]["loc"][0], "body")

    def test_health_check(self) -> None:
        status_code, response = make_request("GET", "/health")

        self.assertEqual(status_code, 200)
        self.assertEqual(response["status"], "healthy")
