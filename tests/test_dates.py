from datetime import date

import pytest

from app.services.dates import InvalidDateError, validate_date

TODAY = date(2026, 10, 4)


@pytest.mark.parametrize("value", [TODAY, date(2026, 9, 20), date(2026, 9, 4)])
def test_dates_within_last_30_days_are_valid(value):
    validate_date(value, today=TODAY)


def test_future_date_is_rejected():
    with pytest.raises(InvalidDateError, match="futura"):
        validate_date(date(2026, 10, 5), today=TODAY)


def test_date_older_than_30_days_is_rejected():
    with pytest.raises(InvalidDateError, match="2026-09-04"):
        validate_date(date(2026, 9, 3), today=TODAY)
