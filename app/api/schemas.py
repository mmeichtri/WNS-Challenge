from datetime import date
from decimal import Decimal
from pydantic import BaseModel


class RecipeSummary(BaseModel):
    id: int
    name: str


class IngredientLine(BaseModel):
    name: str
    quantity_grams: int | None
    purchased_grams: int | None
    cost_ars: Decimal | None


class RecipeCost(BaseModel):
    date: date
    ars: Decimal
    usd: Decimal | None
    ars_per_usd: Decimal | None


class RecipeDetailResponse(BaseModel):
    id: int
    name: str
    instructions: str
    ingredients: list[IngredientLine]
    cost: RecipeCost
    warnings: list[str]


class SimilarRecipeResponse(BaseModel):
    id: int
    name: str
    shared_ingredients: int
