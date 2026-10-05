from decimal import Decimal
from pathlib import Path
from sqlalchemy import Engine, String, create_engine, make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.types import TypeDecorator
from app.core.config import settings


class Base(DeclarativeBase):
    pass


class DecimalText(TypeDecorator):
    impl = String(40)
    cache_ok = True

    def process_bind_param(self, value: Decimal | None, dialect) -> str | None:
        return None if value is None else str(value)

    def process_result_value(self, value: str | None, dialect) -> Decimal | None:
        return None if value is None else Decimal(value)


def make_engine(database_url: str) -> Engine:
    url = make_url(database_url)
    if url.get_backend_name() == "sqlite" and url.database not in (None, "", ":memory:"):
        Path(url.database).parent.mkdir(parents=True, exist_ok=True)

    return create_engine(url)


engine = make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)
