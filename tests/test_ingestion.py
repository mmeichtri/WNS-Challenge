from sqlalchemy import func, select

from app.models import Ingredient, Recipe, RecipeIngredient
from tests.conftest import run_ingestion


def count(session, model) -> int:
    return session.scalar(select(func.count()).select_from(model))


def test_ingestion_loads_all_inputs(session):
    prices_report, recipes_report = run_ingestion(session)

    assert prices_report.created == 45
    assert recipes_report.created == 10
    assert prices_report.rejected == []
    assert recipes_report.rejected == []
    # Sal gruesa, Sal y pimienta y Aceite de oliva no están en ninguna lista de precios.
    assert session.scalar(select(func.count()).where(Ingredient.price_per_kg.is_(None))) == 3


def test_ingestion_is_idempotent(session):
    run_ingestion(session)
    totals_before = (count(session, Ingredient), count(session, Recipe), count(session, RecipeIngredient))

    prices_report, recipes_report = run_ingestion(session)

    assert (count(session, Ingredient), count(session, Recipe), count(session, RecipeIngredient)) == totals_before
    assert (prices_report.created, prices_report.updated, prices_report.unchanged) == (0, 0, 45)
    assert (recipes_report.created, recipes_report.updated, recipes_report.unchanged) == (0, 0, 10)
