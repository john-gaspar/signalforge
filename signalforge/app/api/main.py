from fastapi import FastAPI

from app.api.routes_runs import router as runs_router
from app.core.config import settings

app = FastAPI(
    title=settings.project_name,
    version=settings.version,
    openapi_url=f"{settings.api_prefix}/openapi.json",
)


@app.get("/health", tags=["health"])
def health() -> dict:
    """Lightweight liveness probe."""
    return {"status": "ok", "service": settings.project_name}


app.include_router(runs_router, prefix=settings.api_prefix, tags=["runs"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.api.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=True,
    )
