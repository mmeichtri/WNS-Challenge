"""Cálculo del costo de una receta."""

from dataclasses import dataclass
from decimal import Decimal
from app.models import Recipe, RecipeIngredient

PURCHASE_UNIT_GRAMS = 250
GRAMS_PER_KG = 1000


@dataclass
class IngredientCost:
    name: str
    quantity_grams: int | None
    purchased_grams: int | None
    cost_ars: Decimal | None


@dataclass
class RecipeCost:
    lines: list[IngredientCost]
    total_ars: Decimal

    @property
    def is_complete(self) -> bool:
        return all(line.cost_ars is not None for line in self.lines if line.quantity_grams is not None)


def round_up_to_purchase_unit(grams: int) -> int:
    units = -(-grams // PURCHASE_UNIT_GRAMS)
    return units * PURCHASE_UNIT_GRAMS


def calculate_ingredient_cost(link: RecipeIngredient) -> IngredientCost:
    ingredient = link.ingredient
    if link.quantity_grams is None or ingredient.price_per_kg is None:
        return IngredientCost(ingredient.name, link.quantity_grams, purchased_grams=None, cost_ars=None)

    purchased = round_up_to_purchase_unit(link.quantity_grams)
    cost = Decimal(ingredient.price_per_kg) * purchased / GRAMS_PER_KG
    return IngredientCost(ingredient.name, link.quantity_grams, purchased, cost)


def calculate_recipe_cost(recipe: Recipe) -> RecipeCost:
    lines = [calculate_ingredient_cost(link) for link in recipe.ingredients]
    total = sum((line.cost_ars for line in lines if line.cost_ars is not None), Decimal(0))
    return RecipeCost(lines, total)
