from app.schemas.extract import ExtractedFields
from app.services.grounding import drop_ungrounded

SOURCE = "Invoice INV-1 dated 2026-03-12. Company: Harborline. Total: EUR 1,234.56."
AMOUNT_ONLY = "EUR 1,234.56"


def _fields(**overrides) -> ExtractedFields:
    data = {
        "document_type": "invoice",
        "reference_number": "INV-1",
        "date": "2026-03-12",
        "amount": 1234.56,
        "currency": "EUR",
        "company_name": "Harborline",
        "confidence": 0.95,
    }
    data.update(overrides)
    return ExtractedFields(**data)


def test_honest_amount_is_kept() -> None:
    grounded, dropped = drop_ungrounded(_fields(amount=1234.56), SOURCE)
    assert grounded.amount == 1234.56
    assert "amount" not in dropped


def test_amount_suffixes_and_digit_fragments_are_dropped() -> None:
    for invented in (234.56, 34.56, 4.0, 2.0, 1.0, 42.0):
        grounded, dropped = drop_ungrounded(_fields(amount=invented), AMOUNT_ONLY)
        assert grounded.amount is None, invented
        assert "amount" in dropped, invented
