"""Tipos de datos compartidos entre los parsers y el proceso de ingestión."""

from dataclasses import dataclass, field


@dataclass
class RejectedRow:
    source: str
    location: str | None
    content: str
    reason: str


# --- Precios (Excel y PDF) ---


@dataclass
class ParsedPrice:
    source: str
    location: str
    name: str
    price_per_kg: int


@dataclass
class PriceParseResult:
    prices: list[ParsedPrice] = field(default_factory=list)
    rejected: list[RejectedRow] = field(default_factory=list)


# --- Recetas ---


@dataclass
class ParsedRecipeIngredient:
    name: str
    quantity_grams: int | None


@dataclass
class ParsedRecipe:
    source: str
    location: str
    name: str
    instructions: str
    ingredients: tuple[ParsedRecipeIngredient, ...]


@dataclass
class RecipeParseResult:
    recipes: list[ParsedRecipe] = field(default_factory=list)
    rejected: list[RejectedRow] = field(default_factory=list)
