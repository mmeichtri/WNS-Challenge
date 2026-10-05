"""Parser del PDF de precios de la verdulería."""

import re
import pdfplumber
from app.ingestion.parsers.common import PriceParser, parse_price
from app.ingestion.parsers.schemas import ParsedPrice, PriceParseResult

_PRODUCT_LINE = re.compile(r"(?P<name>.+?)\s+(?P<price>\$\s*\S+)")

class PdfPriceParser(PriceParser):
    def parse(self) -> PriceParseResult:
        result = PriceParseResult()
        with pdfplumber.open(self._path) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                for line_number, line in enumerate(text.splitlines(), start=1):
                    self._parse_line(line.strip(), f"página {page_number}, línea {line_number}", result)
        return result

    def _parse_line(self, line: str, location: str, result: PriceParseResult) -> None:
        if "$" not in line:
            return

        match = _PRODUCT_LINE.fullmatch(line)
        if match is None:
            self._reject(result, location, repr(line), "línea con precio pero sin el formato 'Nombre $precio'")
            return
        try:
            price = parse_price(match["price"])
        except ValueError as exc:
            self._reject(result, location, repr(line), str(exc))
            return

        result.prices.append(ParsedPrice(self._source, location, match["name"].strip(), price))
