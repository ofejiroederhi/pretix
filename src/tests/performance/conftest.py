#
# Fixtures for performance tests (checkout, API timing).
# Defines organizer, event, item, quota so tests/performance/ does not depend on tests/api/conftest.py.
#
from datetime import datetime, timezone
import time

import pytest
from django_scopes import scopes_disabled

from pretix.base.models import Event, Item, ItemCategory, Organizer, Quota


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
def item(event):
    cat = ItemCategory.objects.create(event=event, name="Tickets", position=0)
    return Item.objects.create(
        event=event,
        name="Ticket",
        category=cat,
        default_price=10,
        admission=True,
    )


@pytest.fixture
@scopes_disabled()
def quota(event, item):
    q = Quota.objects.create(event=event, name="Tickets", size=100)
    q.items.add(item)
    return q


@pytest.fixture
def benchmark():
    """Minimal benchmark fixture (pytest-benchmark may not be installed).
    Runs the callable once and returns an object with .duration and .return_value.
    """
    class Result:
        __slots__ = ("duration", "return_value")

        def __init__(self, duration, return_value):
            self.duration = duration
            self.return_value = return_value

    def run(func):
        start = time.perf_counter()
        ret = func()
        return Result(time.perf_counter() - start, ret)

    return run
