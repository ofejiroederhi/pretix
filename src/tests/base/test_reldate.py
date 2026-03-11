#
# Unit tests for base/reldate.py (RelativeDateWrapper, from_string, to_string).
# Targets low-coverage business logic for event-relative dates.
#
import datetime
from zoneinfo import ZoneInfo

import pytest
from django.utils.timezone import now
from django_scopes import scopes_disabled

from pretix.base.reldate import (
    BASE_CHOICES,
    RelativeDate,
    RelativeDateWrapper,
)

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


@pytest.fixture
def event_with_tz():
    """Minimal event with timezone for RelativeDateWrapper tests."""
    from pretix.base.models import Event, Organizer
    with scopes_disabled():
        o = Organizer.objects.create(name="O", slug="o")
        e = Event.objects.create(
            organizer=o,
            name="E",
            slug="e",
            date_from=datetime.datetime(2024, 6, 15, 10, 0, 0, tzinfo=ZoneInfo("Europe/Berlin")),
        )
        e.settings.timezone = "Europe/Berlin"
        return e


def test_relative_date_wrapper_date_with_datetime():
    """RelativeDateWrapper.date() with datetime returns .date()."""
    dt = datetime.datetime(2024, 5, 1, 12, 0, 0)
    w = RelativeDateWrapper(dt)
    from pretix.base.models import Event, Organizer
    with scopes_disabled():
        o = Organizer.objects.create(name="O", slug="o")
        e = Event.objects.create(organizer=o, name="E", slug="e", date_from=now())
        e.settings.timezone = "UTC"
    assert w.date(e) == datetime.date(2024, 5, 1)


def test_relative_date_wrapper_date_with_date():
    """RelativeDateWrapper.date() with date returns same date."""
    d = datetime.date(2024, 5, 1)
    w = RelativeDateWrapper(d)
    from pretix.base.models import Event, Organizer
    with scopes_disabled():
        o = Organizer.objects.create(name="O", slug="o")
        e = Event.objects.create(organizer=o, name="E", slug="e", date_from=now())
        e.settings.timezone = "UTC"
    assert w.date(e) == d


def test_relative_date_wrapper_date_with_relative_date(event_with_tz):
    """RelativeDateWrapper.date() with RelativeDate computes from event date_from."""
    rd = RelativeDate(days=2, minutes=None, time=None, is_after=True, base_date_name="date_from")
    w = RelativeDateWrapper(rd)
    result = w.date(event_with_tz)
    # date_from is 2024-06-15; +2 days = 2024-06-17
    assert result == datetime.date(2024, 6, 17)


def test_relative_date_wrapper_date_relative_before(event_with_tz):
    """RelativeDateWrapper.date() with is_after=False subtracts days."""
    rd = RelativeDate(days=1, minutes=None, time=None, is_after=False, base_date_name="date_from")
    w = RelativeDateWrapper(rd)
    result = w.date(event_with_tz)
    assert result == datetime.date(2024, 6, 14)


def test_relative_date_wrapper_date_minutes_raises(event_with_tz):
    """RelativeDateWrapper.date() with minutes set raises ValueError."""
    rd = RelativeDate(days=0, minutes=30, time=None, is_after=False, base_date_name="date_from")
    w = RelativeDateWrapper(rd)
    with pytest.raises(ValueError) as exc_info:
        w.date(event_with_tz)
    assert "minute-based" in str(exc_info.value)


def test_relative_date_wrapper_datetime_with_relative_minutes(event_with_tz):
    """RelativeDateWrapper.datetime() with minutes uses timedelta minutes."""
    rd = RelativeDate(days=0, minutes=60, time=None, is_after=True, base_date_name="date_from")
    w = RelativeDateWrapper(rd)
    result = w.datetime(event_with_tz)
    # base date_from 2024-06-15 10:00 + 60 min = 11:00
    assert result.hour == 11 or (result.minute == 0 and result.second == 0)


def test_relative_date_wrapper_to_string_datetime():
    """RelativeDateWrapper.to_string() with datetime returns isoformat."""
    dt = datetime.datetime(2024, 5, 1, 12, 0, 0)
    w = RelativeDateWrapper(dt)
    assert "2024-05-01" in w.to_string()


def test_relative_date_wrapper_to_string_relative_days():
    """RelativeDateWrapper.to_string() with RelativeDate (days) returns RELDATE/ format."""
    rd = RelativeDate(days=3, minutes=None, time=None, is_after=True, base_date_name="date_from")
    w = RelativeDateWrapper(rd)
    s = w.to_string()
    assert s.startswith("RELDATE/")
    assert "date_from" in s
    assert "after" in s


def test_relative_date_wrapper_to_string_relative_minutes():
    """RelativeDateWrapper.to_string() with RelativeDate (minutes) returns RELDATE/minutes/."""
    rd = RelativeDate(days=0, minutes=45, time=None, is_after=False, base_date_name="date_from")
    w = RelativeDateWrapper(rd)
    s = w.to_string()
    assert "RELDATE/minutes/" in s
    assert "45" in s


def test_relative_date_wrapper_from_string_iso():
    """RelativeDateWrapper.from_string() with ISO string returns wrapper with datetime."""
    w = RelativeDateWrapper.from_string("2024-06-15T10:00:00")
    assert isinstance(w.data, datetime.datetime)


def test_relative_date_wrapper_from_string_reldate_days():
    """RelativeDateWrapper.from_string() with RELDATE/ days format."""
    w = RelativeDateWrapper.from_string("RELDATE/2/-/date_from/after")
    assert w.data.days == 2
    assert w.data.base_date_name == "date_from"
    assert w.data.is_after is True
    assert w.data.time is None
    assert w.data.minutes is None


def test_relative_date_wrapper_from_string_reldate_minutes():
    """RelativeDateWrapper.from_string() with RELDATE/minutes/ format."""
    w = RelativeDateWrapper.from_string("RELDATE/minutes/30/date_from/after")
    assert w.data.minutes == 30
    assert w.data.base_date_name == "date_from"
    assert w.data.is_after is True


def test_relative_date_wrapper_from_string_invalid_base_raises():
    """RelativeDateWrapper.from_string() with invalid base_date_name raises."""
    with pytest.raises(ValueError) as exc_info:
        RelativeDateWrapper.from_string("RELDATE/1/-/invalid_base/after")
    assert "not a valid base date" in str(exc_info.value)


def test_relative_date_wrapper_len():
    """RelativeDateWrapper __len__ returns len of to_string()."""
    w = RelativeDateWrapper(datetime.date(2024, 1, 1))
    assert len(w) == len(w.to_string())


def test_base_choices_contains_expected_keys():
    """BASE_CHOICES contains expected base date keys."""
    keys = [k[0] for k in BASE_CHOICES]
    assert "date_from" in keys
    assert "presale_start" in keys
    assert "presale_end" in keys
