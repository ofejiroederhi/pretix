#
# Tests for BaseExporter initialization and timezone handling (base/exporter.py).
# Added to improve coverage of a core export path identified via coverage.xml.
#
import pytest
from django.utils.timezone import now
from django_scopes import scopes_disabled

from pretix.base.exporters.events import EventDataExporter
from pretix.base.models import Event, Organizer

pytestmark = [pytest.mark.django_db, pytest.mark.unit]


@pytest.fixture
def organizer_and_event():
    """Minimal organizer and event for exporter tests."""
    with scopes_disabled():
        org = Organizer.objects.create(name="Test Org", slug="test-org")
        event = Event.objects.create(
            organizer=org,
            name="Test Event",
            slug="test-event",
            currency="EUR",
            date_from=now(),
        )
        return org, event


def test_base_exporter_single_event_sets_timezone_and_events(organizer_and_event):
    """BaseExporter with single event sets timezone from event and events queryset."""
    org, event = organizer_and_event
    with scopes_disabled():
        exporter = EventDataExporter(event=event, organizer=org)
    assert exporter.event is event
    assert exporter.organizer is org
    assert exporter.timezone == event.timezone
    with scopes_disabled():
        assert list(exporter.events.values_list("pk", flat=True)) == [event.pk]
    assert exporter.is_multievent is False


def test_base_exporter_multievent_sets_timezone_from_first(organizer_and_event):
    """BaseExporter with event QuerySet sets timezone from first event."""
    org, event = organizer_and_event
    with scopes_disabled():
        events_qs = Event.objects.filter(organizer=org).order_by("pk")
        exporter = EventDataExporter(event=events_qs, organizer=org)
    assert exporter.event is None
    assert exporter.organizer is org
    assert exporter.timezone == event.timezone
    with scopes_disabled():
        assert exporter.events.count() == 1
    assert exporter.is_multievent is True


def test_base_exporter_str_returns_identifier(organizer_and_event):
    """BaseExporter __str__ returns identifier (used in UI)."""
    org, event = organizer_and_event
    with scopes_disabled():
        exporter = EventDataExporter(event=event, organizer=org)
    assert str(exporter) == "eventdata"


def test_base_exporter_description_and_category(organizer_and_event):
    """BaseExporter subclasses can have description and category."""
    org, event = organizer_and_event
    with scopes_disabled():
        exporter = EventDataExporter(event=event, organizer=org)
    assert exporter.description != ""
    assert exporter.category is not None


def test_base_exporter_repeatable_read(organizer_and_event):
    """ListExporter repeatable_read is bool (EventDataExporter uses default)."""
    org, event = organizer_and_event
    with scopes_disabled():
        exporter = EventDataExporter(event=event, organizer=org)
    assert isinstance(exporter.repeatable_read, bool)


def test_base_exporter_available_for_user_default_true(organizer_and_event):
    """BaseExporter.available_for_user returns True by default (e.g. None user)."""
    org, event = organizer_and_event
    with scopes_disabled():
        exporter = EventDataExporter(event=event, organizer=org)
    assert exporter.available_for_user(None) is True


def test_base_exporter_export_form_fields(organizer_and_event):
    """ListExporter has export_form_fields with _format choice."""
    org, event = organizer_and_event
    with scopes_disabled():
        exporter = EventDataExporter(event=event, organizer=org)
    fields = exporter.export_form_fields
    assert "_format" in fields
