from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, Literal

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from app import database


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Initialize persistent storage when the application starts."""

    database.initialize_database()
    yield


app = FastAPI(
    title="Smart Service Request & API Workflow System",
    description=(
        "A minimal API for logging and tracking internal service requests "
        "(e.g. IT/helpdesk tickets) through a pending -> in_progress -> "
        "completed/cancelled workflow. Backed by SQLite for persistence."
    ),
    version="0.1.0",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "health", "description": "Service status endpoints."},
        {"name": "requests", "description": "Create, read, and update service requests."},
    ],
)


RequestStatus = Literal["pending", "in_progress", "completed", "cancelled"]


class ServiceRequestCreate(BaseModel):
    """Data required to create a service request."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "title": "Internet connection issue",
                    "description": "The office internet is unavailable.",
                }
            ]
        },
    )

    title: str = Field(min_length=1, max_length=200, examples=["Internet connection issue"])
    description: str = Field(
        min_length=1,
        max_length=1000,
        examples=["The office internet is unavailable."],
    )


class ServiceRequest(BaseModel):
    """A service request stored by the API."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "title": "Internet connection issue",
                    "description": "The office internet is unavailable.",
                    "status": "pending",
                }
            ]
        }
    )

    id: int
    title: str
    description: str
    status: RequestStatus


class ServiceRequestStatusUpdate(BaseModel):
    """Data required to update a service request status."""

    model_config = ConfigDict(json_schema_extra={"examples": [{"status": "in_progress"}]})

    status: RequestStatus


def find_request(request_id: int) -> ServiceRequest:
    """Return a request by ID or raise a not-found error."""

    request = database.get_request(request_id)
    if request is not None:
        return ServiceRequest(**request)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Service request with ID {request_id} was not found.",
    )


@app.get(
    "/",
    tags=["health"],
    summary="Service info",
    response_description="Basic service metadata",
)
def read_root() -> dict[str, str]:
    """Return a short message confirming the API is running, plus its version."""

    return {
        "message": "Smart Service Request API is running",
        "version": "0.1.0",
    }


@app.get(
    "/health",
    tags=["health"],
    summary="Health check",
    response_description="Current service health",
)
def health_check() -> dict[str, str]:
    """Return a simple liveness signal, used for monitoring/uptime checks."""

    return {
        "status": "healthy",
        "service": "smart-service-request-api",
    }


@app.post(
    "/requests",
    response_model=ServiceRequest,
    status_code=status.HTTP_201_CREATED,
    tags=["requests"],
    summary="Create a service request",
    response_description="The newly created service request",
)
def create_request(request_data: ServiceRequestCreate) -> ServiceRequest:
    """Create and persist a new service request. Status always starts as ``pending``."""

    return ServiceRequest(**database.create_request(request_data.title, request_data.description))


@app.get(
    "/requests",
    response_model=list[ServiceRequest],
    tags=["requests"],
    summary="List service requests",
    response_description="All persisted service requests, ordered by ID",
)
def list_requests() -> list[ServiceRequest]:
    """Return all persisted service requests. Returns an empty list if none exist."""

    return [ServiceRequest(**request) for request in database.list_requests()]


@app.get(
    "/requests/{request_id}",
    response_model=ServiceRequest,
    tags=["requests"],
    summary="Get a service request",
    response_description="The matching service request",
    responses={404: {"description": "No service request exists with the given ID."}},
)
def get_request(request_id: int) -> ServiceRequest:
    """Return one service request by ID."""

    return find_request(request_id)


@app.patch(
    "/requests/{request_id}/status",
    response_model=ServiceRequest,
    tags=["requests"],
    summary="Update a service request's status",
    response_description="The service request with its updated status",
    responses={404: {"description": "No service request exists with the given ID."}},
)
def update_request_status(
    request_id: int,
    status_update: ServiceRequestStatusUpdate,
) -> ServiceRequest:
    """Update the workflow status for one service request."""

    request = database.update_request_status(request_id, status_update.status)
    if request is not None:
        return ServiceRequest(**request)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Service request with ID {request_id} was not found.",
    )


# --- Batch 12: dynamic web dashboard -------------------------------------
# Serves the HTML/CSS/JS frontend that talks to the API endpoints above via
# fetch(). This is presentation only - it adds no new business logic or
# data endpoints; every request the dashboard makes goes through the exact
# same routes and validation defined earlier in this file.

STATIC_DIR = Path(__file__).resolve().parent / "static"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/app", response_class=HTMLResponse, include_in_schema=False)
def serve_dashboard() -> HTMLResponse:
    """Serve the dynamic web dashboard for creating and tracking service requests."""

    index_file = STATIC_DIR / "index.html"
    return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
