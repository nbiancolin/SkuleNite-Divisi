from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from django.test import override_settings

from ensembles.lib.datetime_format import format_part_book_export_datetime


@pytest.mark.django_db
@override_settings(TIME_ZONE="America/Toronto")
def test_format_part_book_export_datetime_eastern():
    # 20:30 UTC on a winter date → 15:30 EST (UTC-5)
    utc = datetime(2026, 1, 15, 20, 30, tzinfo=ZoneInfo("UTC"))
    assert format_part_book_export_datetime(utc) == "2026-01-15 15:30"


@pytest.mark.django_db
@override_settings(TIME_ZONE="America/Toronto")
def test_format_part_book_export_datetime_edt():
    # 20:30 UTC in June → 16:30 EDT (UTC-4)
    utc = datetime(2026, 6, 3, 20, 30, tzinfo=ZoneInfo("UTC"))
    assert format_part_book_export_datetime(utc) == "2026-06-03 16:30"
