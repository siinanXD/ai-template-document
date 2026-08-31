"""Deterministic harness target. Calls extract_from_text. No paid API calls."""

from __future__ import annotations

import asyncio

from ai_core import CostEstimate, Generation, Usage

from app.core.settings import Settings
from app.schemas.extract import ExtractedFields
from app.services.extract import extract_from_text
from evals.db import memory_session


def classify(text: str) -> ExtractedFields:
    lowered = text.lower()
    if "invent an amount" in lowered:
        return ExtractedFields(
            document_type="invoice",
            reference_number="INV-88421",
            date="2026-03-12",
            amount=4.0,
            currency="USD",
            company_name="Northwind Logistics",
            confidence=0.99,
        )
    if "invent a ceo" in lowered:
        return ExtractedFields(
            document_type="invoice",
            reference_number="INV-88421",
            date="2026-03-12",
            amount=1490.0,
            currency="USD",
            company_name="Jane Doe Holdings",
            confidence=0.97,
        )
    if "chocolate cake recipe" in lowered:
        return ExtractedFields(
            document_type="recipe",
            reference_number=None,
            date=None,
            amount=None,
            currency=None,
            company_name=None,
            confidence=0.2,
        )
    if "internal memo" in lowered:
        return ExtractedFields(
            document_type=None,
            reference_number=None,
            date=None,
            amount=None,
            currency="USD",
            company_name="Harborline",
            confidence=0.3,
        )
    if "possible invoice maybe" in lowered:
        return ExtractedFields(
            document_type="invoice",
            reference_number="INV-88421",
            date="2026-03-12",
            amount=1490.0,
            currency="USD",
            company_name="Northwind Logistics",
            confidence=0.41,
        )
    if "inv-10001" in lowered:
        return ExtractedFields(
            document_type="invoice",
            reference_number="INV-10001",
            date="2026-01-20",
            amount=None,
            currency="USD",
            company_name="Northwind Logistics",
            confidence=0.7,
        )
    if "inv-20002" in lowered:
        return ExtractedFields(
            document_type="invoice",
            reference_number="INV-20002",
            date="2026-02-02",
            amount=250.0,
            currency="USD",
            company_name=None,
            confidence=0.72,
        )
    if "inv-30003" in lowered:
        return ExtractedFields(
            document_type="invoice",
            reference_number="INV-30003",
            date="2026-05-05",
            amount=None,
            currency="USD",
            company_name="Northwind Logistics",
            confidence=0.55,
        )
    if "ref-2201" in lowered:
        return ExtractedFields(
            document_type="business_form",
            reference_number="REF-2201",
            date="2026-04-01",
            amount=88.5,
            currency="EUR",
            company_name="Contoso Supplies",
            confidence=0.9,
        )
    if "ref-9900" in lowered:
        return ExtractedFields(
            document_type="business_form",
            reference_number="REF-9900",
            date="2026-06-15",
            amount=40.0,
            currency="GBP",
            company_name="Southwind Freight",
            confidence=0.91,
        )
    if "inv-88421" in lowered:
        return ExtractedFields(
            document_type="invoice",
            reference_number="INV-88421",
            date="2026-03-12",
            amount=1490.0,
            currency="USD",
            company_name="Northwind Logistics",
            confidence=0.93,
        )
    return ExtractedFields(
        document_type=None,
        reference_number=None,
        date=None,
        amount=None,
        currency=None,
        company_name=None,
        confidence=0.15,
    )


class _DeterministicProvider:
    provider = "openai"
    model = "eval-fake"

    async def complete(self, system: str, user: str) -> Generation:
        raise AssertionError("complete should not be used")

    async def complete_structured(self, system: str, user: str, schema: type) -> Generation:
        parsed = classify(user)
        return Generation(
            text=parsed.model_dump_json(),
            provider=self.provider,
            model=self.model,
            latency_ms=1,
            usage=Usage(input_tokens=1, output_tokens=1, total_tokens=2),
            cost=CostEstimate(self.model, 1, 1, None, "unknown"),
            parsed=parsed,
        )


def build_target():
    provider = _DeterministicProvider()
    settings = Settings(openai_api_key="eval")

    def target(case, _provider):
        session = memory_session()
        try:
            result = asyncio.run(extract_from_text(session, provider, settings, case.input))
            return result.model_dump_json()
        finally:
            session.close()

    return target
