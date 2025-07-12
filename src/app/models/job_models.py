from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db.database import Base
from ..enums.job_status import OpenLabsJobStatus
from .mixin_models import OwnableObjectMixin


class JobModel(Base, OwnableObjectMixin):
    """SQLAlchemy ORM model for ARQ jobs."""

    __tablename__ = "jobs"

    # Make this searchable index for worker containers
    arq_job_id: Mapped[str] = mapped_column(
        String, unique=True, index=True, nullable=False
    )
    job_name: Mapped[str] = mapped_column(String, nullable=False)
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
    status: Mapped[OpenLabsJobStatus] = mapped_column(
        Enum(OpenLabsJobStatus), nullable=False
    )
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)

    # Table indexes
    __table_args__ = (Index("ix_jobs_status_finish_time", "status", "finish_time"),)
