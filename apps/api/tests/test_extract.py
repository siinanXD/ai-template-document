from io import BytesIO

from ai_core import ProviderError, RetryExhaustedError, StructuredOutputError
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.dependencies import get_provider
from app.core.settings import Settings
from app.main import app
from app.models.document import DocumentRun
from app.schemas.extract import ExtractedFields
from tests.conftest import INVOICE_TEXT, UNIQUE_SECRET, FakeProvider


def test_valid_document(client: TestClient) -> None:
    response = client.post("/api/v1/documents/extract", json={"text": INVOICE_TEXT})
    assert response.status_code == 200
    body = response.json()
    assert body["document_type"] == "invoice"
    assert body["reference_number"] == "INV-88421"
    assert body["date"] == "2026-03-12"
    assert body["amount"] == 1490.0
    assert body["currency"] == "USD"
    assert body["company_name"] == "Northwind Logistics"
    assert body["confidence"] == 0.92
    assert body["requires_review"] is False
    assert body["model"] == "gpt-4o-mini"
    assert "latency_ms" in body


def test_txt_file_upload(client: TestClient) -> None:
    payload = INVOICE_TEXT.encode("utf-8")
    response = client.post(
        "/api/v1/documents/extract",
        files={"file": ("invoice.txt", payload, "text/plain")},
    )
    assert response.status_code == 200, response.json()
    assert response.json()["reference_number"] == "INV-88421"


def test_unsupported_file(client: TestClient) -> None:
    response = client.post(
        "/api/v1/documents/extract",
        files={"file": ("scan.png", b"\x89PNG\r\n\x1a\nnotpng", "image/png")},
    )
    assert response.status_code == 415
    assert response.json() == {"detail": "unsupported_file"}
    assert "PNG" not in response.text


def test_oversized_file(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.extract.get_settings",
        lambda: Settings(openai_api_key="test", max_upload_bytes=20),
    )
    response = client.post(
        "/api/v1/documents/extract",
        files={"file": ("invoice.txt", b"x" * 40, "text/plain")},
    )
    assert response.status_code == 422
    assert response.json() == {"detail": "invalid_file"}
    assert "xxxx" not in response.text


def test_empty_file(client: TestClient) -> None:
    response = client.post(
        "/api/v1/documents/extract",
        files={"file": ("invoice.txt", b"", "text/plain")},
    )
    assert response.status_code == 422
    assert response.json() == {"detail": "invalid_file"}


def test_empty_json_text(client: TestClient) -> None:
    response = client.post("/api/v1/documents/extract", json={"text": "   "})
    assert response.status_code == 422
    assert response.json() == {"detail": "invalid_request"}


def test_malformed_pdf(client: TestClient) -> None:
    response = client.post(
        "/api/v1/documents/extract",
        files={"file": ("invoice.pdf", b"%PDF-garbage", "application/pdf")},
    )
    assert response.status_code == 422
    assert response.json() == {"detail": "invalid_file"}
    assert "garbage" not in response.text


def test_pdf_with_broken_catalog_returns_422(client: TestClient) -> None:
    payload = b"%PDF-1.1\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n"
    response = client.post(
        "/api/v1/documents/extract",
        files={"file": ("invoice.pdf", payload, "application/pdf")},
    )
    assert response.status_code == 422
    assert response.json() == {"detail": "invalid_file"}
    assert "Root" not in response.text


def test_malformed_extraction_is_ungrounded(
    client: TestClient,
    db_session: Session,
    generation,
) -> None:
    invented = ExtractedFields(
        document_type="invoice",
        reference_number="INV-99999",
        date="1999-01-01",
        amount=999999.0,
        currency="JPY",
        company_name="Invented Corp",
        confidence=0.99,
    )
    app.dependency_overrides[get_provider] = lambda: FakeProvider(
        generation.__class__(
            text=invented.model_dump_json(),
            provider=generation.provider,
            model=generation.model,
            latency_ms=generation.latency_ms,
            usage=generation.usage,
            cost=generation.cost,
            parsed=invented,
        )
    )
    response = client.post("/api/v1/documents/extract", json={"text": INVOICE_TEXT})
    assert response.status_code == 200
    body = response.json()
    assert body["reference_number"] is None
    assert body["date"] is None
    assert body["amount"] is None
    assert body["currency"] is None
    assert body["company_name"] is None
    assert body["requires_review"] is True


def test_invented_amount_suffix_requires_review(
    client: TestClient,
    db_session: Session,
    generation,
) -> None:
    invented = ExtractedFields(
        document_type="invoice",
        reference_number="INV-88421",
        date="2026-03-12",
        amount=4.0,
        currency="USD",
        company_name="Northwind Logistics",
        confidence=0.99,
    )
    app.dependency_overrides[get_provider] = lambda: FakeProvider(
        generation.__class__(
            text=invented.model_dump_json(),
            provider=generation.provider,
            model=generation.model,
            latency_ms=generation.latency_ms,
            usage=generation.usage,
            cost=generation.cost,
            parsed=invented,
        )
    )
    response = client.post("/api/v1/documents/extract", json={"text": INVOICE_TEXT})
    assert response.status_code == 200
    body = response.json()
    assert body["amount"] is None
    assert body["requires_review"] is True


def test_structured_output_failure(
    client: TestClient,
    db_session: Session,
    generation,
) -> None:
    class BadStructuredProvider(FakeProvider):
        async def complete_structured(self, system: str, user: str, schema: type):
            raise StructuredOutputError("could not parse")

    app.dependency_overrides[get_provider] = lambda: BadStructuredProvider(generation)
    response = client.post("/api/v1/documents/extract", json={"text": INVOICE_TEXT})
    assert response.status_code == 502
    assert response.json() == {"detail": "provider_failed"}
    assert INVOICE_TEXT not in response.text


def test_provider_failure(client: TestClient, db_session: Session, generation) -> None:
    from tests.conftest import FailingProvider

    app.dependency_overrides[get_provider] = lambda: FailingProvider(generation)
    response = client.post("/api/v1/documents/extract", json={"text": INVOICE_TEXT})
    assert response.status_code == 502
    assert response.json() == {"detail": "provider_failed"}


def test_retry_exhausted_is_provider_failure(
    client: TestClient, db_session: Session, generation
) -> None:
    class ExhaustingProvider(FakeProvider):
        async def complete_structured(self, system: str, user: str, schema: type):
            raise RetryExhaustedError(
                "gave up after 3 attempts: APITimeoutError",
                attempts=3,
                last_error=TimeoutError("APITimeoutError"),
            )

    app.dependency_overrides[get_provider] = lambda: ExhaustingProvider(generation)
    response = client.post("/api/v1/documents/extract", json={"text": INVOICE_TEXT})
    assert response.status_code == 502
    assert response.json() == {"detail": "provider_failed"}


def test_missing_openai_key_returns_503(db_session: Session, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.core.dependencies.get_settings",
        lambda: Settings(openai_api_key="", database_url="sqlite://"),
    )
    get_provider.cache_clear()

    def _db():
        yield db_session

    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = _db
    with TestClient(app) as test_client:
        response = test_client.post("/api/v1/documents/extract", json={"text": INVOICE_TEXT})
    app.dependency_overrides.clear()
    get_provider.cache_clear()
    assert response.status_code == 503
    assert response.json() == {"detail": "openai_not_configured"}


def test_database_error_returns_503(client: TestClient) -> None:
    from sqlalchemy.exc import OperationalError

    class BoomSession:
        def add(self, *_args, **_kwargs):
            raise OperationalError("INSERT", {}, Exception("down"))

        def execute(self, *_args, **_kwargs):
            raise OperationalError("SELECT", {}, Exception("down"))

        def close(self) -> None:
            return None

    def _db():
        yield BoomSession()

    app.dependency_overrides[get_db] = _db
    response = client.post("/api/v1/documents/extract", json={"text": INVOICE_TEXT})
    assert response.status_code == 503
    assert response.json() == {"detail": "database_unavailable"}


def test_raw_document_is_not_persisted(client: TestClient, db_session: Session) -> None:
    response = client.post("/api/v1/documents/extract", json={"text": UNIQUE_SECRET})
    assert response.status_code == 200
    rows = db_session.query(DocumentRun).all()
    assert len(rows) == 1
    dumped = " ".join(str(value) for value in rows[0].__dict__.values())
    assert UNIQUE_SECRET not in dumped
    assert not hasattr(rows[0], "text")
    assert not hasattr(rows[0], "content")
    assert not hasattr(rows[0], "raw")


def test_low_confidence_requires_review(
    client: TestClient, db_session: Session, generation
) -> None:
    low = ExtractedFields(
        document_type="invoice",
        reference_number="INV-88421",
        date="2026-03-12",
        amount=1490.0,
        currency="USD",
        company_name="Northwind Logistics",
        confidence=0.4,
    )
    app.dependency_overrides[get_provider] = lambda: FakeProvider(
        generation.__class__(
            text=low.model_dump_json(),
            provider=generation.provider,
            model=generation.model,
            latency_ms=generation.latency_ms,
            usage=generation.usage,
            cost=generation.cost,
            parsed=low,
        )
    )
    response = client.post("/api/v1/documents/extract", json={"text": INVOICE_TEXT})
    assert response.status_code == 200
    assert response.json()["requires_review"] is True
    assert response.json()["confidence"] == 0.4


def test_provider_error_type_is_ai_core() -> None:
    assert issubclass(ProviderError, Exception)


def test_errors_do_not_echo_file_bytes(client: TestClient) -> None:
    payload = BytesIO(b"SECRET-BYTES-SHOULD-NOT-LEAK")
    response = client.post(
        "/api/v1/documents/extract",
        files={"file": ("notes.docx", payload.getvalue(), "application/octet-stream")},
    )
    assert response.status_code == 415
    assert "SECRET-BYTES" not in response.text
