"""Display datetime formatting for part-book PDFs."""

from __future__ import annotations

from datetime import datetime

from django.utils import timezone


def format_part_book_export_datetime(dt: datetime | None = None) -> str:
    """
    Format an aware datetime for part-book cover / TOC / tacet pages.

    Uses Django's TIME_ZONE (America/Toronto by default — Eastern Time).
    Output: YYYY-MM-DD HH:MM
    """
    if dt is None:
        dt = timezone.now()
    elif timezone.is_naive(dt):
        dt = timezone.make_aware(dt)

    return timezone.localtime(dt).strftime("%Y-%m-%d %H:%M")
