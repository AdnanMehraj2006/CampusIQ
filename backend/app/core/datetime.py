"""Timezone-safe datetime helpers.

The backend intends every timestamp to be UTC. Columns are declared
``DateTime(timezone=True)`` and all Python-side timestamps are produced with
``datetime.now(timezone.utc)``.

SQLite, however, does not store timezone metadata: an aware UTC value written
to a ``DateTime(timezone=True)`` column comes back *naive* (the offset is
dropped), while PostgreSQL preserves it. Comparing such a reloaded value
against ``datetime.now(timezone.utc)`` therefore raises
``TypeError: can't compare offset-naive and offset-aware datetimes`` on SQLite.

``as_utc`` restores the missing offset. Because every writer in this codebase
stores UTC (via ``func.now()`` or ``datetime.now(timezone.utc)``), interpreting
a naive value as UTC is correct - it only re-attaches the label the column
intended to carry. Use it on *loaded* values before any Python-level
comparison or arithmetic.
"""

from __future__ import annotations

from datetime import datetime, timezone

_UTC = timezone.utc


def as_utc(dt: datetime | None) -> datetime | None:
    """Re-attach the UTC offset to a datetime loaded from the database.

    Naive values are interpreted as UTC (see module docstring); aware values
    are converted to UTC. ``None`` passes through unchanged.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=_UTC)
    return dt.astimezone(_UTC)


def utcnow() -> datetime:
    """Current time as a timezone-aware UTC datetime."""
    return datetime.now(_UTC)
