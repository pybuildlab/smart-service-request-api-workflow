# Changelog

This project's early history (below, "Committed history") predates the
"Batch N" naming convention - those commits aren't individually labeled by
batch number in git. Batch 9 onward is tracked explicitly.

## Unreleased

### Batch 12 - Dynamic website frame + final integration testing

- Added a lightweight HTML/CSS/vanilla-JS dashboard, served at `GET /app`,
  under `app/static/` (`index.html`, `css/style.css`, `js/app.js`). No new
  frameworks or dependencies - CSS/JS are hand-written, and static files
  are served via FastAPI's built-in `StaticFiles` (already part of
  Starlette, a fastapi dependency - no new package required).
- The dashboard creates, lists, and updates the status of service requests
  entirely through the existing, unmodified `/requests` endpoints via
  `fetch()`. It includes a creation form, a live request list with
  status badges, per-request status controls, loading states, and
  success/error feedback. No backend business logic is duplicated
  client-side - validation errors and not-found errors are read directly
  from the API's own response body and displayed as-is.
- `app/main.py`: added a `StaticFiles` mount at `/static` and a new
  `GET /app` route (excluded from the OpenAPI schema) that serves
  `index.html`. Purely additive - every previously existing route, status
  code, and response body is unchanged.
- Added `tests/test_static_frontend.py`: static-asset serving (HTML/CSS/JS
  content types, 404 on unknown assets), confirms `/app` doesn't leak into
  the OpenAPI schema, confirms existing routes are unaffected by the new
  mount, and exercises the exact create/list/update/error contract the
  dashboard's JavaScript depends on.
- Verified against a real running `uvicorn` instance (not just the test
  suite): `/app`, `/static/css/style.css`, and `/static/js/app.js` all
  serve with correct status codes and content types, and a full
  create -> list -> update-status -> get workflow round-trips correctly
  through the SQLite-backed API over real HTTP.
- Full suite: 41 tests passing (32 prior + 9 new), 98% coverage of `app/`.

### Batch 11 - API documentation + workflow polish (Track A: documentation only)

- Added this `CHANGELOG.md`.
- Added `README.md` (setup, run, configuration, endpoint summary, testing).
- Added `docs/api.md` (plain-text endpoint reference with request/response examples).
- Added `.env.example` documenting `SERVICE_REQUEST_DATABASE`.
- Enriched OpenAPI metadata in `app/main.py`: app-level `description` and
  `openapi_tags`, per-route `tags`/`summary`/`response_description`,
  documented `404` responses on the two endpoints that can return one, and
  `examples` on all three Pydantic models.
- No API behavior, status codes, or response bodies changed. No tests
  removed. Track B (behavior changes - status-transition guard, edit/delete
  endpoints, pagination) was scoped out and not implemented.

### Batch 10 - Automated tests

- Added `tests/test_requests_api.py`: root endpoint, unsupported HTTP
  methods (405), unknown routes (404), non-integer/zero/negative IDs, PATCH
  on a missing request (404), missing `status` field (422), empty-list
  state, title/description max-length boundaries, extra-field handling on
  create.
- Added `tests/test_persistence.py`: direct `app/database.py` unit tests -
  `initialize_database()` idempotency, the SQLite `CHECK` constraint on
  `status`, the default-database-path fallback, and CRUD edge cases on
  missing/empty data.
- Added `pytest.ini` (pytest configuration, coverage enabled by default via
  `pytest-cov`).
- Added `requirements-dev.txt` (`pytest`, `pytest-cov` - kept separate from
  production `requirements.txt`).
- All 11 pre-existing tests in `tests/test_health.py` preserved unchanged.
  Full suite: 32 tests passing, 98% coverage of `app/`.

### Batch 9 - SQLite persistence

- Added `app/database.py`: SQLite-backed storage (`initialize_database`,
  `create_request`, `list_requests`, `get_request`, `update_request_status`),
  configurable via the `SERVICE_REQUEST_DATABASE` environment variable, with
  a `CHECK` constraint enforcing valid `status` values at the database
  layer.
- Updated `app/main.py` to use `app/database.py` instead of an in-memory
  list, and added a `lifespan` hook to initialize the database on startup.
- Updated `tests/test_health.py` to point at a temporary SQLite database and
  added persistence-specific test coverage.
- Updated `.gitignore` to exclude the local database file and test/coverage
  artifacts.
- Verified: 11/11 tests passing on the actual project.

## Committed history

Chronological, from `git log`:

- `Intial project setup`
- `Set up FastAPI foundation`
- `Implement minimal FastAPI app`
- `Implement service request endpoints`
- `Implement service request status endpoints`
- `Strengthen request retieval and status tests`
- `Strengthnen requests lifecycle tests`
- `Improve error handling and API validation`

This established the initial FastAPI app with in-memory storage, the
`/requests` CRUD/status endpoints, and the original `tests/test_health.py`
suite (11 tests) - all superseded/extended by Batch 9 and Batch 10 above.
