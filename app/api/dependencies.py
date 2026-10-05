"""Dependencias que FastAPI inyecta en los endpoints."""

from collections.abc import Iterator
from sqlalchemy.orm import Session
from app.clients.currency_api import CurrencyApiClient
from app.core.config import settings
from app.core.db import SessionLocal


def get_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


def get_currency_client() -> CurrencyApiClient:
    return CurrencyApiClient(
        url_templates=[settings.currency_api_url, settings.currency_api_fallback_url],
        timeout_seconds=settings.currency_api_timeout_seconds,
    )
