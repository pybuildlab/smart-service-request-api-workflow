from fastapi import FastAPI, status
from pydantic import BaseModel, ConfigDict, Field


app = FastAPI(
    title="Smart Service Request & API Workflow System",
    version="0.1.0",
)


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
    status: str


service_requests: list[ServiceRequest] = []
next_request_id = 1


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
