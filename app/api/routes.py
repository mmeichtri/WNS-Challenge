from datetime import date
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.api.dependencies import get_currency_client, get_session
from app.api.schemas import IngredientLine, RecipeCost, RecipeDetailResponse, RecipeSummary, SimilarRecipeResponse
from app.clients.currency_api import CurrencyApiClient
from app.services import recipes
from app.services.dates import InvalidDateError

router = APIRouter(prefix="/recipes", tags=["recetas"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.get("", response_model=list[RecipeSummary])
def list_recipes(session: SessionDep):
    return [RecipeSummary(id=recipe.id, name=recipe.name) for recipe in recipes.list_recipes(session)]


@router.get("/{recipe_id}", response_model=RecipeDetailResponse)
def get_recipe(
    recipe_id: int,
    session: SessionDep,
    client: Annotated[CurrencyApiClient, Depends(get_currency_client)],
    rate_date: Annotated[date, Query(alias="date", description="Fecha de cotización, YYYY-MM-DD")],
):
    try:
        detail = recipes.get_recipe_detail(session, recipe_id, rate_date, client)
    except InvalidDateError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    except recipes.RecipeNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc

    return RecipeDetailResponse(
        id=detail.id,
        name=detail.name,
        instructions=detail.instructions,
        ingredients=[
            IngredientLine(
                name=line.name,
                quantity_grams=line.quantity_grams,
                purchased_grams=line.purchased_grams,
                cost_ars=line.cost_ars,
            )
            for line in detail.ingredients
        ],
        cost=RecipeCost(
            date=detail.rate_date,
            ars=detail.total_ars,
            usd=detail.total_usd,
            ars_per_usd=detail.ars_per_usd,
        ),
        warnings=detail.warnings,
    )


@router.get("/{recipe_id}/similar", response_model=list[SimilarRecipeResponse])
def get_similar_recipes(recipe_id: int, session: SessionDep):
    try:
        similar = recipes.find_similar_recipes(session, recipe_id)
    except recipes.RecipeNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc

    return [SimilarRecipeResponse(id=s.id, name=s.name, shared_ingredients=s.shared_ingredients) for s in similar]
