from fastapi import FastAPI
from app.api.routes_runs import router as runs_router

app = FastAPI(title="SignalForge API")
app.include_router(runs_router, prefix="/runs", tags=["runs"])
