from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base, DecimalText, engine


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    normalized_name: Mapped[str] = mapped_column(String(200), unique=True)
    instructions: Mapped[str] = mapped_column(Text)
    ingredients: Mapped[list["RecipeIngredient"]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan", order_by="RecipeIngredient.position"
    )


class Ingredient(Base):
    __tablename__ = "ingredients"
    __table_args__ = (
        CheckConstraint("price_per_kg IS NULL OR price_per_kg > 0", name="ck_ingredients_price_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    normalized_name: Mapped[str] = mapped_column(String(100), unique=True)
    price_per_kg: Mapped[int | None]

    recipes: Mapped[list["RecipeIngredient"]] = relationship(back_populates="ingredient")


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"
    __table_args__ = (
        CheckConstraint("quantity_grams IS NULL OR quantity_grams > 0", name="ck_recipe_ingredients_quantity_positive"),
    )

    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"), primary_key=True)
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id"), primary_key=True)
    quantity_grams: Mapped[int | None]
    position: Mapped[int]

    recipe: Mapped[Recipe] = relationship(back_populates="ingredients")
    ingredient: Mapped[Ingredient] = relationship(back_populates="recipes")


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"

    rate_date: Mapped[date] = mapped_column(primary_key=True)
    ars_per_usd: Mapped[Decimal] = mapped_column(DecimalText)
    fetched_at: Mapped[datetime]


def init_db() -> None:
    Base.metadata.create_all(engine)
