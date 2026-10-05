from datetime import date
from decimal import Decimal

from app.models import ExchangeRate
from app.services.exchange_rates import get_ars_per_usd
from tests.conftest import FakeCurrencyClient

DAY = date(2026, 10, 1)


def test_rate_is_fetched_once_and_then_read_from_the_database(session):
    client = FakeCurrencyClient({DAY: Decimal("1524.86175585")})

    first = get_ars_per_usd(session, DAY, client)
    second = get_ars_per_usd(session, DAY, client)

    assert first == second == Decimal("1524.86175585")
    assert client.calls == [DAY]
    assert session.get(ExchangeRate, DAY).ars_per_usd == Decimal("1524.86175585")
