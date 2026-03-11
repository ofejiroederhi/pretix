#
# Fixtures for security tests (OWASP, access control, etc.).
# Defines organizer, event, event2, user so tests/security/ does not depend on tests/api/conftest.py.
#
from datetime import datetime, timezone

import pytest
from django_scopes import scopes_disabled

from pretix.base.models import Event, Organizer, Team, User


@pytest.fixture
@scopes_disabled()
def organizer():
    return Organizer.objects.create(name="Dummy", slug="dummy")


@pytest.fixture
@scopes_disabled()
def event(organizer):
    return Event.objects.create(
        organizer=organizer,
        name="Dummy",
        slug="dummy",
        date_from=datetime(2017, 12, 27, 10, 0, 0, tzinfo=timezone.utc),
        is_public=True,
        live=True,
    )


@pytest.fixture
@scopes_disabled()
def event2(organizer):
    return Event.objects.create(
        organizer=organizer,
        name="Dummy2",
        slug="dummy2",
        date_from=datetime(2017, 12, 27, 10, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
@scopes_disabled()
def user(organizer, event):
    user = User.objects.create_user("dummy@dummy.dummy", "dummy")
    team = Team.objects.create(
        organizer=organizer,
        name="Test-Team",
        all_events=False,
        can_view_orders=True,
        can_change_event_settings=True,
    )
    team.members.add(user)
    team.limit_events.add(event)
    return user
