"""Obtención y cache de la cotización ARS por USD."""

import logging
from datetime import UTC, date, datetime
from decimal import Decimal
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session
from app.clients.currency_api import CurrencyApiClient, CurrencyApiError
from app.models import ExchangeRate

logger = logging.getLogger(__name__)


class ExchangeRateUnavailable(Exception):
    """No hay cotización para la fecha: no está en la base y la API no respondió."""


def get_ars_per_usd(session: Session, rate_date: date, client: CurrencyApiClient) -> Decimal:
    cached = session.get(ExchangeRate, rate_date)
    if cached is not None:
        return cached.ars_per_usd

    try:
        rate = client.fetch_ars_per_usd(rate_date)
    except CurrencyApiError as exc:
        raise ExchangeRateUnavailable(str(exc)) from exc
    logger.info("Cotización obtenida para %s: %s ARS/USD", rate_date.isoformat(), rate)

    session.execute(
        insert(ExchangeRate)
        .values(rate_date=rate_date, ars_per_usd=rate, fetched_at=datetime.now(UTC))
        .on_conflict_do_nothing(index_elements=["rate_date"])
    )
    session.commit()
    return rate
