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

    def test_request_requires_title_and_description(self) -> None:
        status_code, _ = make_request("POST", "/requests", {"title": ""})

        self.assertEqual(status_code, 422)

    def test_health_check(self) -> None:
        status_code, response = make_request("GET", "/health")

        self.assertEqual(status_code, 200)
        self.assertEqual(response["status"], "healthy")
