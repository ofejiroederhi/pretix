#
# This file is part of pretix (Community Edition).
#
# Copyright (C) 2014-2020  Raphael Michel and contributors
# Copyright (C) 2020-today pretix GmbH and contributors
#
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General
# Public License as published by the Free Software Foundation in version 3 of the License.
#
# ADDITIONAL TERMS APPLY: Pursuant to Section 7 of the GNU Affero General Public License, additional terms are
# applicable granting you additional permissions and placing additional restrictions on your usage of this software.
# Please refer to the pretix LICENSE file to obtain the full terms applicable to this work. If you did not receive
# this file, see <https://pretix.eu/about/en/license>.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY and FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License along with this program.  If not, see
# <https://www.gnu.org/licenses/>.
#

#
# Fixtures for performance tests (checkout, API timing).
# Defines organizer, event, item, quota so tests/performance/ does not depend on tests/api/conftest.py.
#
import time
from datetime import datetime, timezone

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
