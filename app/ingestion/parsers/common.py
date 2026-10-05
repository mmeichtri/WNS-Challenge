"""Clases y utilidades compartidas por los parsers de precios."""

import logging
import re
from abc import ABC, abstractmethod
from pathlib import Path
from app.ingestion.parsers.schemas import PriceParseResult, RejectedRow

logger = logging.getLogger(__name__)


# Enteros con o sin separador de miles y con "$" opcional: "6800", "6.000", "$2600", "$1.200".
_PRICE_TEXT = re.compile(r"\$?\s*(\d{1,3}(?:\.\d{3})+|\d+)")


def parse_price(value: object) -> int:
    if isinstance(value, bool):
        raise ValueError(f"precio inválido: {value!r}")
    if isinstance(value, int):
        price = value
    elif isinstance(value, float):
        if not value.is_integer():
            raise ValueError(f"precio con decimales no soportado: {value!r}")
        price = int(value)
    elif isinstance(value, str):
        match = _PRICE_TEXT.fullmatch(value.strip())
        if match is None:
            raise ValueError(f"formato de precio no reconocido: {value!r}")
        price = int(match.group(1).replace(".", ""))
    else:
        raise ValueError(f"precio inválido: {value!r}")

    if price <= 0:
        raise ValueError(f"el precio debe ser mayor a cero: {value!r}")
    return price


class PriceParser(ABC):
    """Contrato de un parser de precios: lee un archivo y devuelve precios y rechazos.

    El manager trabaja con PriceParseResult sin saber de qué formato viene, así
    que sumar una fuente nueva (ej. un CSV) es sumar una subclase.
    """

    def __init__(self, path: Path):
        self._path = path
        self._source = path.name

    @abstractmethod
    def parse(self) -> PriceParseResult: ...

    def _reject(self, result: PriceParseResult, location: str | None, content: str, reason: str) -> None:
        logger.warning("Registro rechazado (%s, %s): %s -> %s", self._source, location, content, reason)
        result.rejected.append(RejectedRow(self._source, location, content, reason))
