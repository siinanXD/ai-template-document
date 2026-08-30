from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class DocumentRun(Base):
    __tablename__ = "document_runs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    file_hash: Mapped[str] = mapped_column(String(64), index=True)
    document_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reference_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    extracted_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    company_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    confidence: Mapped[float] = mapped_column(Float)
    requires_review: Mapped[bool] = mapped_column(Boolean)
    model: Mapped[str] = mapped_column(String(128))
    latency_ms: Mapped[int] = mapped_column(Integer)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
