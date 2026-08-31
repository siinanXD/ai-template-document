from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ExtractTextRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20000)

    @field_validator("text")
    @classmethod
    def not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped


class ExtractedFields(BaseModel):
    """Structured model output. Used by ai-core complete_structured."""

    document_type: str | None = None
    reference_number: str | None = None
    date: str | None = None
    amount: float | None = None
    currency: str | None = None
    company_name: str | None = None
    confidence: float = Field(ge=0, le=1)

    @field_validator("document_type", "reference_number", "date", "company_name")
    @classmethod
    def empty_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped.upper() or None


class ExtractResponse(BaseModel):
    id: UUID
    document_type: str | None
    reference_number: str | None
    date: str | None
    amount: float | None
    currency: str | None
    company_name: str | None
    confidence: float
    requires_review: bool
    model: str
    latency_ms: int
    generation_latency_ms: int
    input_tokens: int | None
    output_tokens: int | None
    estimated_cost_usd: float | None
    created_at: datetime
