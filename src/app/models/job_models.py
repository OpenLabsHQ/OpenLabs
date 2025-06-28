from datetime import datetime
from typing import Any

from arq.jobs import JobStatus
from sqlalchemy import Boolean, DateTime, Enum, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db.database import Base
from .mixin_models import OwnableObjectMixin


class JobModel(Base, OwnableObjectMixin):
    """SQLAlchemy ORM model for ARQ jobs."""

    job_id: Mapped[str] = mapped_column(String, nullable=False)
    function: Mapped[str] = mapped_column(String, nullable=False)
    job_try: Mapped[int | None] = mapped_column(Integer, nullable=True)
    enqueue_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    start_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finish_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), nullable=False)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
