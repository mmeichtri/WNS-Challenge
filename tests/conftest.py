"""Fixtures compartidas por los tests.

Ningún test usa la red ni data/app.db: la base es SQLite en memoria y la
cotización sale de un cliente falso (o de requests.get reemplazado).
"""

import os

os.environ["DATABASE_URL"] = "sqlite://"

from datetime import date
from decimal import Decimal
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.api.dependencies import get_currency_client, get_session
from app.clients.currency_api import CurrencyApiError
from app.core.db import Base
from app.ingestion.manager import ingest_prices, ingest_recipes
from app.ingestion.parsers.excel_parser import ExcelPriceParser
from app.ingestion.parsers.pdf_parser import PdfPriceParser
from app.ingestion.parsers.recipe_parser import RecipeParser
from app.main import app

INPUTS_DIR = Path(__file__).resolve().parent.parent / "inputs"


class FakeCurrencyClient:
    """Reemplaza a CurrencyApiClient: devuelve cotizaciones fijas y cuenta las llamadas."""

    def __init__(self, rates: dict[date, Decimal]) -> None:
        self.rates = rates
        self.calls: list[date] = []

    def fetch_ars_per_usd(self, rate_date: date) -> Decimal:
        self.calls.append(rate_date)
        if rate_date not in self.rates:
            raise CurrencyApiError(f"No se pudo obtener la cotización del {rate_date.isoformat()}")
        return self.rates[rate_date]


@pytest.fixture
def session():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def run_ingestion(session: Session) -> tuple:
    price_results = [
        ExcelPriceParser(INPUTS_DIR / "Carnes y Pescados.xlsx").parse(),
        PdfPriceParser(INPUTS_DIR / "verduleria.pdf").parse(),
    ]
    prices_report = ingest_prices(session, price_results)
    session.flush()
    recipes_report = ingest_recipes(session, RecipeParser(INPUTS_DIR / "Recetas.md").parse())
    session.commit()
    return prices_report, recipes_report


@pytest.fixture
def seeded_session(session):
    """Base en memoria cargada con los archivos de inputs reales."""
    run_ingestion(session)
    return session


@pytest.fixture
def api_client(seeded_session):
    """Fábrica de TestClient con la base en memoria: cada test pasa las cotizaciones que existen."""

    def make(rates: dict[date, Decimal]) -> TestClient:
        fake = FakeCurrencyClient(rates)
        app.dependency_overrides[get_session] = lambda: seeded_session
        app.dependency_overrides[get_currency_client] = lambda: fake
        return TestClient(app)

    yield make
    app.dependency_overrides.clear()
