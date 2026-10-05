from datetime import date, timedelta
from decimal import Decimal

import pytest

# Fechas relativas a hoy: validate_date usa date.today().
YESTERDAY = date.today() - timedelta(days=1)
RATE = Decimal("1524.86175585")


@pytest.fixture
def client(api_client):
    return api_client({YESTERDAY: RATE})


def recipe_id(client, name: str) -> int:
    return next(recipe["id"] for recipe in client.get("/recipes").json() if recipe["name"] == name)


def test_recipe_detail_with_cost_in_ars_and_usd(client):
    asado = recipe_id(client, "Asado con ensalada criolla")

    response = client.get(f"/recipes/{asado}", params={"date": YESTERDAY.isoformat()})

    assert response.status_code == 200
    body = response.json()
    assert body["instructions"].startswith("Cortar las verduras")
    cebolla = next(line for line in body["ingredients"] if line["name"] == "Cebolla")
    assert (cebolla["quantity_grams"], cebolla["purchased_grams"], cebolla["cost_ars"]) == (400, 500, "450.00")
    # 6800 + 300 + 450 + 375 = 7925 ARS; 7925 / 1524.86175585 = 5.197... USD
    assert body["cost"] == {"date": YESTERDAY.isoformat(), "ars": "7925.00", "usd": "5.20", "ars_per_usd": str(RATE)}
    assert body["warnings"] == []


def test_recipe_detail_keeps_ingredients_in_recipe_order(client):
    ensalada = recipe_id(client, "Ensalada de atún (merluza) con espinaca")

    response = client.get(f"/recipes/{ensalada}", params={"date": YESTERDAY.isoformat()})

    names = [line["name"] for line in response.json()["ingredients"]]
    assert names == ["Merluza fresca", "Espinaca", "Tomate", "Pepino", "Sal y pimienta"]


def test_recipe_detail_without_exchange_rate_still_returns_ars(api_client):
    client = api_client({})
    asado = recipe_id(client, "Asado con ensalada criolla")

    response = client.get(f"/recipes/{asado}", params={"date": YESTERDAY.isoformat()})

    assert response.status_code == 200
    body = response.json()
    assert body["cost"]["ars"] == "7925.00"
    assert body["cost"]["usd"] is None
    assert "cotización del dólar" in body["warnings"][0]


def test_unknown_recipe_returns_404(client):
    response = client.get("/recipes/999", params={"date": YESTERDAY.isoformat()})

    assert response.status_code == 404
    assert response.json() == {"detail": "No existe la receta 999"}


@pytest.mark.parametrize(
    "params",
    [
        {"date": (date.today() + timedelta(days=1)).isoformat()},
        {"date": "2026-13-45"},
    ],
    ids=["futura", "formato invalido"],
)
def test_invalid_date_returns_422(client, params):
    response = client.get("/recipes/1", params=params)

    assert response.status_code == 422


def test_similar_recipes_sorted_by_shared_ingredients(client):
    asado = recipe_id(client, "Asado con ensalada criolla")

    response = client.get(f"/recipes/{asado}/similar")

    assert response.status_code == 200
    similar = response.json()
    # Asado comparte Tomate y Cebolla con Berenjenas, y Morrón y Cebolla con Lomo.
    assert [(r["name"], r["shared_ingredients"]) for r in similar[:2]] == [
        ("Berenjenas rellenas con carne picada", 2),
        ("Lomo salteado con brócoli y morrón", 2),
    ]
    assert all(r["shared_ingredients"] == 1 for r in similar[2:])
    assert "Asado con ensalada criolla" not in [r["name"] for r in similar]
    # Supremas no comparte ningún ingrediente con el asado.
    assert "Supremas de pollo con puré de zapallo y brócoli" not in [r["name"] for r in similar]
