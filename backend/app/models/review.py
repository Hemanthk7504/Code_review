"""Review history database model for persistent audit & risk tracking."""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ReviewRecordModel(Base):
    __tablename__ = "review_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: uuid4().hex[:12])
    target_path: Mapped[str] = mapped_column(String(256), nullable=False)
    files_analyzed: Mapped[int] = mapped_column(Integer, default=1)
    total_findings: Mapped[int] = mapped_column(Integer, default=0)
    verified_findings: Mapped[int] = mapped_column(Integer, default=0)
    overall_risk: Mapped[float] = mapped_column(Float, default=0.0)
    posture_grade: Mapped[str] = mapped_column(String(8), default="A+")
    findings_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[str] = mapped_column(
        String(64),
        default=lambda: datetime.now(timezone.utc).isoformat()
    )
