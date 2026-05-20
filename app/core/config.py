from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "MVP Facturacion DIAN"
    debug: bool = True
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 1440
    allow_public_register: bool = True

    database_url: str = "postgresql://postgres:postgres@localhost:5432/facturacion_dian"

    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    storage_path: str = "./data/documents"
    dian_adapter: str = "mock"
    mock_dian_accept_rate: float = 1.0

    cors_origins: List[str] = ["http://localhost:8000", "http://127.0.0.1:8000"]

    # Invoice / credit note prefixes (TODO-DIAN: from DIAN resolution)
    invoice_prefix: str = "SETT"
    credit_note_prefix: str = "NC"
    debit_note_prefix: str = "ND"


@lru_cache
def get_settings() -> Settings:
    return Settings()
