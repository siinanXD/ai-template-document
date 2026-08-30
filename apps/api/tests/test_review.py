from app.schemas.extract import ExtractedFields
from app.services.review import requires_review


def _complete(**overrides) -> ExtractedFields:
    data = {
        "document_type": "invoice",
        "reference_number": "INV-1",
        "date": "2026-03-12",
        "amount": 10.0,
        "currency": "USD",
        "company_name": "Harborline",
        "confidence": 0.9,
    }
    data.update(overrides)
    return ExtractedFields(**data)


def test_complete_high_confidence_does_not_need_review() -> None:
    assert requires_review(_complete(), 0.75) is False


def test_low_confidence_requires_review() -> None:
    assert requires_review(_complete(confidence=0.4), 0.75) is True


def test_missing_required_field_requires_review() -> None:
    assert requires_review(_complete(amount=None), 0.75) is True
    assert requires_review(_complete(reference_number=None), 0.75) is True
    assert requires_review(_complete(company_name=None), 0.75) is True
    assert requires_review(_complete(date=None), 0.75) is True
    assert requires_review(_complete(currency=None), 0.75) is True


def test_unknown_document_type_requires_review() -> None:
    assert requires_review(_complete(document_type="recipe"), 0.75) is True
    assert requires_review(_complete(document_type=None), 0.75) is True


def test_invented_fields_force_review() -> None:
    assert requires_review(_complete(), 0.75, invented_dropped=True) is True
