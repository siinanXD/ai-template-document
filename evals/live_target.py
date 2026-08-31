"""Optional live OpenAI target. Refuses to run unless explicitly enabled."""

from __future__ import annotations

import asyncio
import os

from app.core.dependencies import get_provider
from app.core.settings import get_settings
from app.services.extract import extract_from_text
from evals.db import memory_session


def build_target():
    if os.getenv("RUN_OPENAI_EVAL") != "1":
        raise RuntimeError("refusing live OpenAI evals without RUN_OPENAI_EVAL=1")
    get_settings.cache_clear()
    get_provider.cache_clear()
    provider = get_provider()
    settings = get_settings()

    def target(case, _provider):
        session = memory_session()
        try:
            result = asyncio.run(extract_from_text(session, provider, settings, case.input))
            return result.model_dump_json()
        finally:
            session.close()

    return target
