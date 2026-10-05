from decimal import Decimal

from app.models import Ingredient, Recipe, RecipeIngredient
from app.services.costing import calculate_recipe_cost


def make_recipe(*items: tuple[str, int | None, int | None]) -> Recipe:
    """Arma una receta en memoria (sin base) con tuplas (nombre, gramos, precio por kg)."""
    recipe = Recipe(name="Test", normalized_name="test", instructions="")
    recipe.ingredients = [
        RecipeIngredient(
            ingredient=Ingredient(name=name, normalized_name=name.lower(), price_per_kg=price),
            quantity_grams=grams,
        )
        for name, grams, price in items
    ]
    return recipe


def test_recipe_cost_rounds_each_ingredient_up_to_250_g():
    # Ejemplo de la consigna: 800 g de zapallo se cotizan como 1 kg.
    recipe = make_recipe(("Zapallo", 800, 700), ("Papa", 250, 850))

    cost = calculate_recipe_cost(recipe)

    assert [line.purchased_grams for line in cost.lines] == [1000, 250]
    assert cost.total_ars == Decimal("700") + Decimal("212.5")
    assert cost.is_complete


def test_to_taste_ingredients_do_not_add_cost_and_keep_cost_complete():
    recipe = make_recipe(("Cebolla", 400, 900), ("Sal gruesa", None, None))

    cost = calculate_recipe_cost(recipe)

    assert cost.total_ars == Decimal("450")
    assert cost.lines[1].cost_ars is None
    assert cost.is_complete
