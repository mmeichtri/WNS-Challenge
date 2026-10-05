"""Cliente HTTP para obtener la cotización USD -> ARS."""

import logging
from datetime import date
from decimal import Decimal
import requests

logger = logging.getLogger(__name__)


class CurrencyApiError(Exception):
    """No se pudo obtener la cotización de ninguna de las URLs."""


class InvalidCurrencyApiResponse(Exception):
    """La API respondió 200 pero con un contenido que no sirve."""


class CurrencyApiClient:
    def __init__(self, url_templates: list[str], timeout_seconds: float) -> None:
        self.url_templates = url_templates
        self.timeout_seconds = timeout_seconds

    def fetch_ars_per_usd(self, rate_date: date) -> Decimal:
        for template in self.url_templates:
            url = template.format(date=rate_date.isoformat())
            try:
                return self._fetch_from(url)
            except (requests.RequestException, InvalidCurrencyApiResponse) as exc:
                logger.warning("Falló la consulta de cotización a %s: %s", url, exc)

        raise CurrencyApiError(f"No se pudo obtener la cotización del {rate_date.isoformat()}")

    def _fetch_from(self, url: str) -> Decimal:
        response = requests.get(url, timeout=self.timeout_seconds)
        response.raise_for_status()

        try:
            data = response.json(parse_float=Decimal)
        except ValueError as exc:
            raise InvalidCurrencyApiResponse("la respuesta no es un JSON válido") from exc

        if not isinstance(data, dict) or not isinstance(data.get("usd"), dict):
            raise InvalidCurrencyApiResponse("la respuesta no tiene el objeto usd")

        value = data["usd"].get("ars")
        if value is None:
            raise InvalidCurrencyApiResponse("la respuesta no tiene la cotización ars")
        if not isinstance(value, (int, Decimal)):
            raise InvalidCurrencyApiResponse(f"la cotización ars no es un número, es {type(value).__name__}")
        if value <= 0:
            raise InvalidCurrencyApiResponse(f"la cotización ars debe ser positiva: {value}")

        return Decimal(value)
