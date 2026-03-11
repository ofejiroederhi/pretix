#
# Unit tests for base/timeline.py (timeline_for_event function).
# Targets low-coverage control/timeline logic.
#
import datetime
from zoneinfo import ZoneInfo

import pytest
from django_scopes import scopes_disabled

from pretix.base.models import Event, Organizer
from pretix.base.timeline import TimelineEvent, timeline_for_event

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


@pytest.fixture
def minimal_event():
    """Minimal event for timeline tests."""
    with scopes_disabled():
        o = Organizer.objects.create(name="Org", slug="org")
        e = Event.objects.create(
            organizer=o,
            name="Ev",
            slug="ev",
            date_from=datetime.datetime(2024, 7, 1, 14, 0, 0, tzinfo=ZoneInfo("UTC")),
        )
        return e


def test_timeline_for_event_returns_list(minimal_event):
    """timeline_for_event returns a list of TimelineEvent."""
    from django_scopes import scopes_disabled
    with scopes_disabled():
        tl = timeline_for_event(minimal_event)
    assert isinstance(tl, list)
    assert len(tl) >= 1


def test_timeline_for_event_first_entry_is_event_starts(minimal_event):
    """First timeline entry describes event start."""
    from django_scopes import scopes_disabled
    with scopes_disabled():
        tl = timeline_for_event(minimal_event)
    assert len(tl) >= 1
    first = tl[0]
    assert isinstance(first, TimelineEvent)
    assert first.event is minimal_event
    assert first.subevent is None
    assert first.datetime == minimal_event.date_from
    assert "start" in str(first.description).lower()


def test_timeline_for_event_includes_date_to_when_set(minimal_event):
    """When date_to is set, timeline includes event end."""
    from django_scopes import scopes_disabled
    with scopes_disabled():
        minimal_event.date_to = datetime.datetime(
            2024, 7, 2, 18, 0, 0, tzinfo=ZoneInfo("UTC")
        )
        minimal_event.save()
        tl = timeline_for_event(minimal_event)
    datetimes = [t.datetime for t in tl]
    assert minimal_event.date_to in datetimes or any(
        d == minimal_event.date_to for d in datetimes
    )


def test_timeline_for_event_edit_url_contains_organizer_and_event(minimal_event):
    """Timeline edit URLs contain event and organizer slugs."""
    from django_scopes import scopes_disabled
    with scopes_disabled():
        tl = timeline_for_event(minimal_event)
    assert len(tl) >= 1
    edit_url = tl[0].edit_url
    assert minimal_event.slug in edit_url
    assert minimal_event.organizer.slug in edit_url
