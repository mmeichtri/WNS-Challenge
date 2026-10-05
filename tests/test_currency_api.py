"""Tests del cliente HTTP: requests.get se reemplaza con monkeypatch, sin red."""

from datetime import date
from decimal import Decimal

import pytest
import requests

from app.clients.currency_api import CurrencyApiClient, CurrencyApiError

PRIMARY = "https://primary.test/{date}.json"
FALLBACK = "https://fallback.test/{date}.json"


def make_response(status_code: int, body: str) -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    response._content = body.encode()
    return response


def ok(rate: str = "1500.25") -> requests.Response:
    return make_response(200, '{"date": "2026-10-01", "usd": {"ars": ' + rate + "}}")


def timeout() -> requests.Response:
    raise requests.Timeout("timed out")


@pytest.fixture
def fake_api(monkeypatch):
    """Configura qué responde cada URL. Devuelve la lista de URLs consultadas."""
    requested_urls = []

    def configure(primary, fallback):
        def fake_get(url, timeout):
            requested_urls.append(url)
            handler = primary if url.startswith("https://primary.test") else fallback
            return handler()

        monkeypatch.setattr(requests, "get", fake_get)
        return requested_urls

    return configure


@pytest.fixture
def client():
    return CurrencyApiClient([PRIMARY, FALLBACK], timeout_seconds=1)


def test_uses_primary_url_with_the_date(fake_api, client):
    requested = fake_api(primary=lambda: ok("1524.86175585"), fallback=timeout)

    rate = client.fetch_ars_per_usd(date(2026, 10, 1))

    assert rate == Decimal("1524.86175585")
    assert requested == ["https://primary.test/2026-10-01.json"]


@pytest.mark.parametrize(
    "primary_failure",
    [
        timeout,
        lambda: make_response(500, ""),
        lambda: make_response(200, "<html>no es json</html>"),
    ],
    ids=["timeout", "500", "html"],
)
def test_falls_back_when_primary_fails(fake_api, client, primary_failure):
    requested = fake_api(primary=primary_failure, fallback=ok)

    assert client.fetch_ars_per_usd(date(2026, 10, 1)) == Decimal("1500.25")
    assert len(requested) == 2


def test_raises_when_both_urls_fail(fake_api, client):
    fake_api(primary=timeout, fallback=lambda: make_response(503, ""))

    with pytest.raises(CurrencyApiError):
        client.fetch_ars_per_usd(date(2026, 10, 1))
