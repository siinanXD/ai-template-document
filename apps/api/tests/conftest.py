from collections.abc import Generator

import pytest
from ai_core import CostEstimate, Generation, Usage
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import Base, get_db
from app.core.dependencies import get_provider
from app.main import app
from app.models import DocumentRun  # noqa: F401
from app.schemas.extract import ExtractedFields

INVOICE_TEXT = (
    "Harborline Invoice INV-88421 dated 2026-03-12.\n"
    "Bill to: Northwind Logistics.\n"
    "Amount due: 1490.00 USD.\n"
    "Pay to Harborline Billing."
)

UNIQUE_SECRET = "UNIQUE-CUSTOMER-DOCUMENT-INV-88421-NORTHWIND"


@pytest.fixture
def extracted_fields() -> ExtractedFields:
    return ExtractedFields(
        document_type="invoice",
        reference_number="INV-88421",
        date="2026-03-12",
        amount=1490.0,
        currency="USD",
        company_name="Northwind Logistics",
        confidence=0.92,
    )


@pytest.fixture
def generation(extracted_fields: ExtractedFields) -> Generation:
    return Generation(
        text=extracted_fields.model_dump_json(),
        provider="openai",
        model="gpt-4o-mini",
        latency_ms=18,
        usage=Usage(input_tokens=11, output_tokens=22, total_tokens=33),
        cost=CostEstimate("gpt-4o-mini", 11, 22, 0.0002, "known"),
        parsed=extracted_fields,
    )


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


class FakeProvider:
    provider = "openai"
    model = "gpt-4o-mini"

    def __init__(self, generation: Generation) -> None:
        self._generation = generation
        self.calls: list[tuple[str, str, type]] = []

    async def complete(self, system: str, user: str) -> Generation:
        raise AssertionError("complete should not be used")

    async def complete_structured(self, system: str, user: str, schema: type) -> Generation:
        self.calls.append((system, user, schema))
        return self._generation


class FailingProvider(FakeProvider):
    async def complete_structured(self, system: str, user: str, schema: type) -> Generation:
        from ai_core import ProviderError

        raise ProviderError("upstream failed")


@pytest.fixture
def fake_provider(generation: Generation) -> FakeProvider:
    return FakeProvider(generation)


@pytest.fixture
def client(
    db_session: Session,
    fake_provider: FakeProvider,
) -> Generator[TestClient, None, None]:
    def _db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_provider] = lambda: fake_provider
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
