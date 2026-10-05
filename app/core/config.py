import logging
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "WNS Challenge"
    debug: bool = False
    log_level: str = "INFO"
    database_url: str = "sqlite:///./data/app.db"
    excel_prices_path: Path = Path("inputs/Carnes y Pescados.xlsx")
    pdf_prices_path: Path = Path("inputs/verduleria.pdf")
    recipes_path: Path = Path("inputs/Recetas.md")
    currency_api_url: str = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{date}/v1/currencies/usd.json"
    currency_api_fallback_url: str = "https://{date}.currency-api.pages.dev/v1/currencies/usd.json"
    currency_api_timeout_seconds: float = 5.0


settings = Settings()


def configure_logging() -> None:
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
