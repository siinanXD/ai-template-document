from app.schemas.extract import ExtractedFields

KNOWN_TYPES = frozenset({"invoice", "business_form"})
REQUIRED_FIELDS = ("reference_number", "date", "amount", "currency", "company_name")


def requires_review(
    fields: ExtractedFields,
    threshold: float,
    *,
    invented_dropped: bool = False,
) -> bool:
    if invented_dropped:
        return True
    if fields.confidence < threshold:
        return True
    if fields.document_type not in KNOWN_TYPES:
        return True
    return any(getattr(fields, name) is None for name in REQUIRED_FIELDS)
