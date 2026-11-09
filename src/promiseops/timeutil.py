"""Time helpers. All timestamps are stored as UTC ISO-8601 strings and shown in market local time."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

UTC = timezone.utc


def parse(value: str | None) -> datetime | None:
    if not value:
        return None
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError(f"Timestamp without time zone: {value!r}")
    return dt.astimezone(UTC)


def iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        raise ValueError("Naive datetime is not allowed")
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def local(dt: datetime | str | None, tz: str, fmt: str = "%H:%M") -> str:
    if isinstance(dt, str):
        dt = parse(dt)
    if dt is None:
        return "-"
    return dt.astimezone(ZoneInfo(tz)).strftime(fmt)


def local_dt(day: str, hhmm: str, tz: str) -> datetime:
    """Build an aware datetime from a local calendar day and HH:MM in the given zone."""
    naive = datetime.fromisoformat(f"{day}T{hhmm}:00")
    return naive.replace(tzinfo=ZoneInfo(tz)).astimezone(UTC)


def minutes_between(start: datetime, end: datetime) -> int:
    return int((end - start) / timedelta(minutes=1))


def fmt_minutes(minutes: int) -> str:
    sign = "-" if minutes < 0 else ""
    m = abs(minutes)
    if m >= 60:
        return f"{sign}{m // 60}h {m % 60:02d}m"
    return f"{sign}{m}m"
