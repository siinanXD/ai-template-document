"""Drop extracted values that do not appear in the source text.

The model must not invent required values silently. A missing value stays missing.
"""

from __future__ import annotations

import re

from app.schemas.extract import ExtractedFields

_CURRENCY_MARKS: dict[str, tuple[str, ...]] = {
    "USD": ("usd", "$"),
    "EUR": ("eur", "€"),
    "GBP": ("gbp", "£"),
}


def drop_ungrounded(fields: ExtractedFields, source_text: str) -> tuple[ExtractedFields, list[str]]:
    haystack = source_text.lower()
    compact = re.sub(r"[\s,]", "", haystack)
    dropped: list[str] = []

    reference_number = fields.reference_number
    if reference_number and reference_number.lower() not in haystack:
        reference_number = None
        dropped.append("reference_number")

    date = fields.date
    if date and date.lower() not in haystack:
        date = None
        dropped.append("date")

    company_name = fields.company_name
    if company_name and company_name.lower() not in haystack:
        company_name = None
        dropped.append("company_name")

    currency = fields.currency
    if currency:
        marks = _CURRENCY_MARKS.get(currency, (currency.lower(),))
        if not any(mark in haystack for mark in marks):
            currency = None
            dropped.append("currency")

    amount = fields.amount
    if amount is not None and not _amount_in_text(amount, compact):
        amount = None
        dropped.append("amount")

    grounded = fields.model_copy(
        update={
            "reference_number": reference_number,
            "date": date,
            "amount": amount,
            "currency": currency,
            "company_name": company_name,
        }
    )
    return grounded, dropped


def _amount_in_text(amount: float, compact_lower: str) -> bool:
    whole = f"{amount:.2f}".rstrip("0").rstrip(".")
    candidates = {whole, f"{amount:.2f}"}
    if amount == int(amount):
        candidates.add(f"{int(amount)}")
    return any(_digit_bounded(candidate, compact_lower) for candidate in candidates)


def _digit_bounded(candidate: str, compact_lower: str) -> bool:
    return re.search(rf"(?<![\d.]){re.escape(candidate)}(?![\d])", compact_lower) is not None
