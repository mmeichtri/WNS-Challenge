import logging
from app.core.config import configure_logging, settings
from app.core.db import SessionLocal
from app.ingestion.manager import IngestionReport, ingest_prices, ingest_recipes
from app.ingestion.parsers.common import PriceParser
from app.ingestion.parsers.excel_parser import ExcelPriceParser
from app.ingestion.parsers.pdf_parser import PdfPriceParser
from app.ingestion.parsers.recipe_parser import RecipeParser
from app.models import init_db

logger = logging.getLogger(__name__)


def _log_summary(label: str, report: IngestionReport) -> None:
    logger.info(
        "Ingesta de %s: %d creados, %d actualizados, %d sin cambios, %d rechazados",
        label,
        report.created,
        report.updated,
        report.unchanged,
        len(report.rejected),
    )


def main() -> int:
    configure_logging()
    init_db()

    try:
        price_parsers: list[PriceParser] = [
            ExcelPriceParser(settings.excel_prices_path),
            PdfPriceParser(settings.pdf_prices_path),
        ]
        price_results = [parser.parse() for parser in price_parsers]
        recipe_result = RecipeParser(settings.recipes_path).parse()
    except FileNotFoundError as exc:
        logger.error("No se encontró el archivo de entrada: %s", exc.filename)
        return 1

    with SessionLocal.begin() as session:
        prices_report = ingest_prices(session, price_results)
        session.flush()
        recipes_report = ingest_recipes(session, recipe_result)

    _log_summary("precios", prices_report)
    _log_summary("recetas", recipes_report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
