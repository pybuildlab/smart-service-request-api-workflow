from fastapi import FastAPI


app = FastAPI(
    title="Smart Service Request & API Workflow System",
    version="0.1.0",
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
