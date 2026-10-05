import pytest

from app.ingestion.parsers.common import parse_price
from app.ingestion.parsers.excel_parser import ExcelPriceParser
from app.ingestion.parsers.pdf_parser import PdfPriceParser
from app.ingestion.parsers.recipe_parser import RecipeParser
from tests.conftest import INPUTS_DIR


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(6800, 6800), ("6.000", 6000), ("$2600", 2600)],
)
def test_parse_price_accepts_known_formats(raw, expected):
    assert parse_price(raw) == expected


def test_excel_parser_reads_real_file():
    result = ExcelPriceParser(INPUTS_DIR / "Carnes y Pescados.xlsx").parse()

    assert len(result.prices) == 29
    assert result.rejected == []
    first = result.prices[0]
    assert (first.name, first.price_per_kg, first.location) == ("Asado de tira", 6800, "fila 5")


def test_pdf_parser_reads_real_file():
    result = PdfPriceParser(INPUTS_DIR / "verduleria.pdf").parse()

    assert len(result.prices) == 16
    assert result.rejected == []
    assert {"Tomate": 1200, "Cebolla": 900}.items() <= {p.name: p.price_per_kg for p in result.prices}.items()


def test_recipe_parser_reads_real_file():
    result = RecipeParser(INPUTS_DIR / "Recetas.md").parse()

    assert len(result.recipes) == 10
    assert result.rejected == []
    asado = next(recipe for recipe in result.recipes if recipe.name == "Asado con ensalada criolla")
    assert {i.name: i.quantity_grams for i in asado.ingredients}["Sal gruesa"] is None


def test_recipe_parser_reports_rejected_line_and_keeps_the_rest(tmp_path):
    recipes_file = tmp_path / "Recetas.md"
    recipes_file.write_text(
        "# Guiso\n"
        "## Ingredientes\n"
        "- 500 g de Papa\n"
        "- 2 litros de Agua\n"
        "## Instrucciones\n"
        "Hervir todo.\n",
        encoding="utf-8",
    )

    result = RecipeParser(recipes_file).parse()

    # La línea inválida se informa con ubicación y motivo...
    assert len(result.rejected) == 1
    rejected = result.rejected[0]
    assert (rejected.source, rejected.location) == ("Recetas.md", "línea 4")
    assert "unidad no reconocida" in rejected.reason
    # ...y el resto de la receta se carga igual.
    assert [(i.name, i.quantity_grams) for i in result.recipes[0].ingredients] == [("Papa", 500)]
