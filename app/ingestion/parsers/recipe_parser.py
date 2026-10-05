"""Parser de Recetas.md.

Interpreta recetas, secciones, ingredientes e instrucciones y registra
rechazos indicando la línea de origen.
"""
import logging
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from app.ingestion.normalization import normalize_name
from app.ingestion.parsers.schemas import ParsedRecipe, ParsedRecipeIngredient, RecipeParseResult, RejectedRow

logger = logging.getLogger(__name__)

TO_TASTE = "a gusto"

_INGREDIENTS = "ingredients"
_INSTRUCTIONS = "instructions"
_UNKNOWN = "unknown"

@dataclass
class _RecipeDraft:
    name: str
    location: str
    ingredients: dict[str, ParsedRecipeIngredient] = field(default_factory=dict)
    instruction_lines: list[str] = field(default_factory=list)


def parse_quantity(text: str) -> int | None:
    text = normalize_name(text)
    if text == TO_TASTE:
        return None

    if text.endswith("kg"):
        number, grams_per_unit = text.removesuffix("kg").strip(), 1000
    elif text.endswith("g"):
        number, grams_per_unit = text.removesuffix("g").strip(), 1
    else:
        raise ValueError(f"unidad no reconocida (se aceptan g, kg y 'a gusto'): '{text}'")

    if not number.replace(",", "", 1).isdecimal():
        raise ValueError(f"cantidad no reconocida: '{text}'")

    grams = Decimal(number.replace(",", ".")) * grams_per_unit
    if grams != grams.to_integral_value():
        raise ValueError(f"cantidad con fracciones de gramo: '{text}'")
    if grams <= 0:
        raise ValueError(f"la cantidad debe ser mayor a cero: '{text}'")
    return int(grams)


def parse_ingredient(item: str) -> ParsedRecipeIngredient:
    if ":" in item:
        name, quantity = item.split(":", 1)
    elif item.lower().endswith(" " + TO_TASTE):
        name, quantity = item[:-len(TO_TASTE)], TO_TASTE
    elif " de " in item:
        quantity, name = item.split(" de ", 1)
    else:
        raise ValueError(f"formato de ingrediente no reconocido: '{item}'")

    name = name.strip()
    if not name:
        raise ValueError(f"ingrediente sin nombre: '{item}'")
    return ParsedRecipeIngredient(name, parse_quantity(quantity))


def split_heading(line: str) -> tuple[int, str]:
    text = line.lstrip("#")
    level = len(line) - len(text)  # cuántos "#" había al principio
    if level == 0 or not text.startswith(" ") or not text.strip():
        return 0, line
    return level, text.strip()


def remove_list_marker(line: str) -> str:
    first_word, _, rest = line.partition(" ")
    if first_word in ("-", "*"):
        return rest.strip()
    if first_word.endswith("."):
        marker = first_word[:-1]
        if marker.isdecimal() or (len(marker) == 1 and marker.isalpha()):
            return rest.strip()
    return line


class RecipeParser:
    def __init__(self, path: Path):
        self._path = path
        self._source = path.name

    def parse(self) -> RecipeParseResult:
        result = RecipeParseResult()
        draft: _RecipeDraft | None = None
        section: str | None = None

        lines = self._path.read_text(encoding="utf-8").splitlines()
        for line_number, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            location = f"línea {line_number}"
            if not line:
                continue

            level, title = split_heading(line)
            if level == 1:
                if draft is not None:
                    self._finish(draft, result)
                draft = _RecipeDraft(title, location)
                section = None
                continue

            if draft is None:
                self._reject(result, location, line, "texto antes de la primera receta")
                continue

            if level > 1:
                section = self._classify_section(title)
                if section == _UNKNOWN:
                    self._reject(result, location, line, f"sección desconocida en la receta '{draft.name}'")
                continue

            if section == _INGREDIENTS:
                self._add_ingredient(draft, line, location, result)
            elif section == _INSTRUCTIONS:
                draft.instruction_lines.append(line)
            elif section is None:
                self._reject(result, location, line, f"texto fuera de una sección en la receta '{draft.name}'")

        if draft is not None:
            self._finish(draft, result)
        return result

    @staticmethod
    def _classify_section(title: str) -> str:
        normalized = normalize_name(title)
        if "ingrediente" in normalized or normalized == "lista":
            return _INGREDIENTS
        if "instruccion" in normalized or "preparacion" in normalized:
            return _INSTRUCTIONS
        return _UNKNOWN

    def _add_ingredient(self, draft: _RecipeDraft, line: str, location: str, result: RecipeParseResult) -> None:
        try:
            ingredient = parse_ingredient(remove_list_marker(line))
        except ValueError as exc:
            self._reject(result, location, line, str(exc))
            return

        key = normalize_name(ingredient.name)
        previous = draft.ingredients.get(key)
        if previous is not None:
            ingredient = ParsedRecipeIngredient(previous.name, _sum_quantities(previous, ingredient))
            logger.info(
                "Ingrediente repetido en '%s' (%s): %s, se suman las cantidades -> %s g",
                draft.name,
                location,
                previous.name,
                ingredient.quantity_grams,
            )
        draft.ingredients[key] = ingredient

    def _finish(self, draft: _RecipeDraft, result: RecipeParseResult) -> None:
        if not draft.ingredients:
            self._reject(result, draft.location, draft.name, "receta sin ingredientes válidos")
            return
        if not draft.instruction_lines:
            self._reject(result, draft.location, draft.name, "receta sin instrucciones")
            return

        result.recipes.append(
            ParsedRecipe(
                source=self._source,
                location=draft.location,
                name=draft.name,
                instructions="\n".join(draft.instruction_lines),
                ingredients=tuple(draft.ingredients.values()),
            )
        )

    def _reject(self, result: RecipeParseResult, location: str, content: str, reason: str) -> None:
        logger.warning("Registro rechazado (%s, %s): '%s' -> %s", self._source, location, content, reason)
        result.rejected.append(RejectedRow(self._source, location, content, reason))


def _sum_quantities(a: ParsedRecipeIngredient, b: ParsedRecipeIngredient) -> int | None:
    if a.quantity_grams is None and b.quantity_grams is None:
        return None
    return (a.quantity_grams or 0) + (b.quantity_grams or 0)
