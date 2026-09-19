from typing import Literal

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field


app = FastAPI(
    title="Smart Service Request & API Workflow System",
    version="0.1.0",
)


RequestStatus = Literal["pending", "in_progress", "completed", "cancelled"]


class ServiceRequestCreate(BaseModel):
    """Data required to create a service request."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=1000)


class ServiceRequest(BaseModel):
    """A service request stored by the API."""

    id: int
    title: str
    description: str
    status: RequestStatus


class ServiceRequestStatusUpdate(BaseModel):
    """Data required to update a service request status."""

    status: RequestStatus


service_requests: list[ServiceRequest] = []
next_request_id = 1


def find_request(request_id: int) -> ServiceRequest:
    """Return a request by ID or raise a not-found error."""

    for request in service_requests:
        if request.id == request_id:
            return request

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Service request with ID {request_id} was not found.",
    )


@app.get("/")
def read_root() -> dict[str, str]:
    return {
        "message": "Smart Service Request API is running",
        "version": "0.1.0",
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": "smart-service-request-api",
    }


@app.post(
    "/requests",
    response_model=ServiceRequest,
    status_code=status.HTTP_201_CREATED,
)
def create_request(request_data: ServiceRequestCreate) -> ServiceRequest:
    """Create and store a new service request in memory."""

    global next_request_id

    request = ServiceRequest(
        id=next_request_id,
        title=request_data.title,
        description=request_data.description,
        status="pending",
    )
    service_requests.append(request)
    next_request_id += 1
    return request


@app.get("/requests", response_model=list[ServiceRequest])
def list_requests() -> list[ServiceRequest]:
    """Return all service requests currently stored in memory."""

    return service_requests


@app.get("/requests/{request_id}", response_model=ServiceRequest)
def get_request(request_id: int) -> ServiceRequest:
    """Return one service request by ID."""

    return find_request(request_id)


@app.patch("/requests/{request_id}/status", response_model=ServiceRequest)
def update_request_status(
    request_id: int,
    status_update: ServiceRequestStatusUpdate,
) -> ServiceRequest:
    """Update the workflow status for one service request."""

    request = find_request(request_id)
    request.status = status_update.status
    return request
