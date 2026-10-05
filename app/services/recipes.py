"""Casos de uso de recetas."""

import logging
from dataclasses import dataclass, replace
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased, selectinload
from app.clients.currency_api import CurrencyApiClient
from app.models import Recipe, RecipeIngredient
from app.services.costing import IngredientCost, calculate_recipe_cost
from app.services.dates import validate_date
from app.services.exchange_rates import ExchangeRateUnavailable, get_ars_per_usd

logger = logging.getLogger(__name__)

CENTS = Decimal("0.01")


class RecipeNotFound(Exception):
    """No existe una receta con ese id."""


@dataclass
class RecipeDetail:
    id: int
    name: str
    instructions: str
    rate_date: date
    ingredients: list[IngredientCost]
    total_ars: Decimal
    ars_per_usd: Decimal | None
    total_usd: Decimal | None
    warnings: list[str]


@dataclass
class SimilarRecipe:
    id: int
    name: str
    shared_ingredients: int


def list_recipes(session: Session) -> list[Recipe]:
    return list(session.scalars(select(Recipe).order_by(Recipe.name)))


def get_recipe_detail(session: Session, recipe_id: int, rate_date: date, client: CurrencyApiClient) -> RecipeDetail:
    # Si la fecha es inválida no tiene sentido ir a la base ni a la API.
    validate_date(rate_date)

    recipe = session.scalar(
        select(Recipe)
        .where(Recipe.id == recipe_id)
        .options(selectinload(Recipe.ingredients).selectinload(RecipeIngredient.ingredient))
    )
    if recipe is None:
        raise RecipeNotFound(f"No existe la receta {recipe_id}")

    cost = calculate_recipe_cost(recipe)
    total_ars = cost.total_ars.quantize(CENTS, ROUND_HALF_UP)
    warnings = []

    missing_prices = [line.name for line in cost.lines if line.quantity_grams is not None and line.cost_ars is None]
    if missing_prices:
        warnings.append(f"El costo no incluye ingredientes sin precio: {', '.join(missing_prices)}")

    ars_per_usd = None
    total_usd = None
    try:
        ars_per_usd = get_ars_per_usd(session, rate_date, client)
        total_usd = (cost.total_ars / ars_per_usd).quantize(CENTS, ROUND_HALF_UP)
    except ExchangeRateUnavailable as exc:
        # La cotización depende de un servicio externo: si no está, se informa el costo en ARS (que no depende de la API) y se avisa que falta USD.
        logger.error("Sin cotización para la receta %s: %s", recipe_id, exc)
        warnings.append(f"No se pudo obtener la cotización del dólar para el {rate_date.isoformat()}")

    return RecipeDetail(
        id=recipe.id,
        name=recipe.name,
        instructions=recipe.instructions,
        rate_date=rate_date,
        ingredients=[_round_line(line) for line in cost.lines],
        total_ars=total_ars,
        ars_per_usd=ars_per_usd,
        total_usd=total_usd,
        warnings=warnings,
    )


def _round_line(line: IngredientCost) -> IngredientCost:
    if line.cost_ars is None:
        return line
    return replace(line, cost_ars=line.cost_ars.quantize(CENTS, ROUND_HALF_UP))


def find_similar_recipes(session: Session, recipe_id: int) -> list[SimilarRecipe]:
    if session.get(Recipe, recipe_id) is None:
        raise RecipeNotFound(f"No existe la receta {recipe_id}")

    # join para contar ingredientes compartidos con cada otra receta
    mine = aliased(RecipeIngredient)
    other = aliased(RecipeIngredient)
    shared = func.count().label("shared")

    rows = session.execute(
        select(Recipe.id, Recipe.name, shared)
        .join(other, other.recipe_id == Recipe.id)
        .join(mine, mine.ingredient_id == other.ingredient_id)
        .where(mine.recipe_id == recipe_id, other.recipe_id != recipe_id)
        .group_by(Recipe.id, Recipe.name)
        .order_by(shared.desc(), Recipe.name)
    )
    return [SimilarRecipe(id=row.id, name=row.name, shared_ingredients=row.shared) for row in rows]
