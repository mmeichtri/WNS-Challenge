"""Carga en la base de datos los resultados de los parsers"""

import logging
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.normalization import normalize_name
from app.ingestion.parsers.schemas import ParsedPrice, ParsedRecipe, PriceParseResult, RecipeParseResult, RejectedRow
from app.models import Ingredient, Recipe, RecipeIngredient

logger = logging.getLogger(__name__)


@dataclass
class IngestionReport:
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    rejected: list[RejectedRow] = field(default_factory=list)

    def reject(self, source: str, location: str, content: str, reason: str) -> None:
        logger.warning("Registro rechazado (%s, %s): %r -> %s", source, location, content, reason)
        self.rejected.append(RejectedRow(source, location, repr(content), reason))


def save_ingredient_prices(session: Session, prices: list[ParsedPrice]) -> IngestionReport:
    report = IngestionReport()
    existing = {ingredient.normalized_name: ingredient for ingredient in session.scalars(select(Ingredient))}
    seen: dict[str, ParsedPrice] = {}

    for item in prices:
        key = normalize_name(item.name)

        if key in seen:
            reason = f"ingrediente duplicado (ya cargado en {seen[key].source}, {seen[key].location})"
            report.reject(item.source, item.location, item.name, reason)
            continue
        seen[key] = item

        ingredient = existing.get(key)
        if not ingredient:
            session.add(Ingredient(name=item.name, normalized_name=key, price_per_kg=item.price_per_kg))
            report.created += 1
        elif ingredient.price_per_kg == item.price_per_kg:
            report.unchanged += 1
        else:
            logger.info("Precio actualizado: %s %s -> %s", item.name, ingredient.price_per_kg, item.price_per_kg)
            ingredient.price_per_kg = item.price_per_kg
            report.updated += 1

    return report


def save_recipes(session: Session, recipes: list[ParsedRecipe]) -> IngestionReport:
    report = IngestionReport()
    ingredients = {ingredient.normalized_name: ingredient for ingredient in session.scalars(select(Ingredient))}
    existing = {recipe.normalized_name: recipe for recipe in session.scalars(select(Recipe))}
    seen: dict[str, ParsedRecipe] = {}

    for parsed in recipes:
        key = normalize_name(parsed.name)

        if key in seen:
            report.reject(parsed.source, parsed.location, parsed.name, f"receta duplicada (ya cargada en {seen[key].location})")
            continue
        seen[key] = parsed

        desired = {
            _get_or_create_ingredient(session, ingredients, item.name, parsed.name): item.quantity_grams
            for item in parsed.ingredients
        }

        recipe = existing.get(key)
        if recipe is None:
            recipe = Recipe(name=parsed.name, normalized_name=key, instructions=parsed.instructions)
            session.add(recipe)
            report.created += 1
        else:
            # Se compara como lista para que un cambio de orden también cuente como actualización.
            current = [(link.ingredient, link.quantity_grams) for link in recipe.ingredients]
            if (
                recipe.name == parsed.name
                and recipe.instructions == parsed.instructions
                and current == list(desired.items())
            ):
                report.unchanged += 1
                continue

            logger.info("Receta actualizada: %s", parsed.name)
            recipe.name = parsed.name
            recipe.instructions = parsed.instructions
            recipe.ingredients.clear()
            # Se borran los ingredientes viejos antes de insertar los nuevos para evitar conflictos de PK
            session.flush()
            report.updated += 1

        recipe.ingredients.extend(
            RecipeIngredient(ingredient=ingredient, quantity_grams=quantity, position=position)
            for position, (ingredient, quantity) in enumerate(desired.items())
        )

    return report


def _get_or_create_ingredient(
    session: Session, ingredients: dict[str, Ingredient], name: str, recipe_name: str
) -> Ingredient:
    key = normalize_name(name)
    ingredient = ingredients.get(key)
    if ingredient is None:
        logger.warning("Ingrediente sin precio en ninguna lista: %r (receta %r)", name, recipe_name)
        ingredient = Ingredient(name=name, normalized_name=key, price_per_kg=None)
        session.add(ingredient)
        ingredients[key] = ingredient
    return ingredient


def ingest_prices(session: Session, parse_results: list[PriceParseResult]) -> IngestionReport:
    # Se guardan todas las fuentes juntas para detectar también un mismo ingrediente repetido entre el Excel y el PDF.
    prices = [price for result in parse_results for price in result.prices]
    report = save_ingredient_prices(session, prices)
    report.rejected = [row for result in parse_results for row in result.rejected] + report.rejected
    return report


def ingest_recipes(session: Session, parse_result: RecipeParseResult) -> IngestionReport:
    report = save_recipes(session, parse_result.recipes)
    report.rejected = parse_result.rejected + report.rejected
    return report
