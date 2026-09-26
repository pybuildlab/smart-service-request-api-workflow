# API Reference

Base URL (local dev): `http://127.0.0.1:8000`

This is a static reference. The live, always-up-to-date schema is served by
the app itself at `/docs` (Swagger UI), `/redoc`, and `/openapi.json`.

This document covers the JSON API only. There is also a browser dashboard
at `/app` (with its assets under `/static/`) that consumes the endpoints
below via `fetch()` - it's a plain HTML page, not a JSON endpoint, so it's
not listed as a numbered entry here. See the README's "Web dashboard"
section for details.

Service requests move through this status workflow:

```
pending -> in_progress -> completed
                       \-> cancelled
```

`status` transitions are not currently restricted - any request can be moved
to any of the four status values via the status-update endpoint.

---

## GET /

Service info.

**Response `200`**
```json
{
  "message": "Smart Service Request API is running",
  "version": "0.1.0"
}
```

---

## GET /health

Health check, for monitoring/uptime checks.

**Response `200`**
```json
{
  "status": "healthy",
  "service": "smart-service-request-api"
}
```

---

## POST /requests

Create a new service request. `status` always starts as `"pending"` and
cannot be set by the client.

**Request body**

| Field | Type | Required | Constraints |
|---|---|---|---|
| `title` | string | Yes | 1-200 characters, whitespace-only rejected |
| `description` | string | Yes | 1-1000 characters, whitespace-only rejected |

```json
{
  "title": "Internet connection issue",
  "description": "The office internet is unavailable."
}
```

**Response `201`**
```json
{
  "id": 1,
  "title": "Internet connection issue",
  "description": "The office internet is unavailable.",
  "status": "pending"
}
```

**Response `422`** - validation error (missing/empty/too-long `title` or
`description`).

---

## GET /requests

List all service requests, ordered by ID.

**Response `200`**
```json
[
  {
    "id": 1,
    "title": "Internet connection issue",
    "description": "The office internet is unavailable.",
    "status": "pending"
  }
]
```

Returns `[]` when no requests exist.

---

## GET /requests/{id}

Get one service request by ID.

**Path parameters**

| Name | Type | Notes |
|---|---|---|
| `id` | integer | Non-integer values return `422` |

**Response `200`** - same shape as the create response.

**Response `404`**
```json
{
  "detail": "Service request with ID 999 was not found."
}
```

---

## PATCH /requests/{id}/status

Update only the status of an existing service request.

**Path parameters**

| Name | Type | Notes |
|---|---|---|
| `id` | integer | Non-integer values return `422` |

**Request body**

| Field | Type | Required | Allowed values |
|---|---|---|---|
| `status` | string | Yes | `pending`, `in_progress`, `completed`, `cancelled` |

```json
{
  "status": "in_progress"
}
```

**Response `200`** - the full service request with its updated status.

**Response `404`** - no request exists with the given ID (same shape as
`GET /requests/{id}`'s 404).

**Response `422`** - `status` missing or not one of the four allowed values.

---

## Error format

Validation errors (`422`) follow FastAPI's default shape:

```json
{
  "detail": [
    {
      "type": "literal_error",
      "loc": ["body", "status"],
      "msg": "...",
      "input": "..."
    }
  ]
}
```

Not-found errors (`404`) use a single string `detail` message rather than
the list form above.
