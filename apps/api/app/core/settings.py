from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://starter:starter@localhost:5434/starter"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_timeout_seconds: float = 30
    openai_input_usd_per_mtok: float | None = None
    openai_output_usd_per_mtok: float | None = None
    cors_origins: str = "http://localhost:3000"
    max_upload_bytes: int = 1_048_576
    max_extract_chars: int = 20_000
    review_confidence_threshold: float = 0.75

    @field_validator("database_url")
    @classmethod
    def use_psycopg(cls, value: str) -> str:
        if value.startswith("postgresql://"):
            return "postgresql+psycopg://" + value.removeprefix("postgresql://")
        if value.startswith("postgres://"):
            return "postgresql+psycopg://" + value.removeprefix("postgres://")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
