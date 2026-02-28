from fastapi import FastAPI, Response, status
from app.api.routes_runs import router as runs_router

app = FastAPI(title="SignalForge API")
app.include_router(runs_router, prefix="/runs", tags=["runs"])


@app.get("/health")
def health():
    return {"status": "ok"}
