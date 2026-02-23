from fastapi import FastAPI
from app.core.db import Base, engine
from app.api.routes_runs import router as runs_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="SignalForge API")
app.include_router(runs_router, prefix="/runs", tags=["runs"])