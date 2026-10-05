"""Validación de fechas para la cotización de recetas."""

from datetime import date, timedelta

MAX_DAYS_BACK = 30


class InvalidDateError(Exception):
    """La fecha está fuera del rango permitido."""


def validate_date(value: date, today: date | None = None) -> None:
    if today is None:
        today = date.today()

    oldest_allowed = today - timedelta(days=MAX_DAYS_BACK)

    if value > today:
        raise InvalidDateError(f"La fecha {value.isoformat()} es futura: tiene que ser hoy o anterior")
    if value < oldest_allowed:
        raise InvalidDateError(
            f"La fecha {value.isoformat()} es demasiado antigua: "
            f"tiene que estar entre {oldest_allowed.isoformat()} y {today.isoformat()}"
        )
