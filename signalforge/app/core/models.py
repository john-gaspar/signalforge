from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field
from sqlalchemy import JSON, Column, DateTime, String, func

from app.core.db import Base


class Run(BaseModel):
    """Lightweight representation returned by the API."""

    id: str
    status: str = "queued"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RunRecord(Base):
    __tablename__ = "runs"

    id = Column(String, primary_key=True, index=True)
    status = Column(String, default="queued", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    payload = Column(JSON, nullable=True)


__all__ = ["Run", "RunRecord"]
