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
# Unit tests for pretix.plugins.statistics signals (nav_event, clear_cache).
# Targets: statistics/signals.py (coverage was ~78%, improve to >75% and exercise clear_cache).
#
from datetime import datetime, timezone

import pytest

from pretix.base.models import Event, Organizer
from pretix.plugins.statistics.signals import clear_cache


@pytest.fixture
def organizer():
    return Organizer.objects.create(name="Test Org", slug="test-org")


@pytest.fixture
def event(organizer):
    return Event.objects.create(
        organizer=organizer,
        name="Test Event",
        slug="test-event",
        date_from=datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
        plugins="pretix.plugins.statistics",
    )


@pytest.mark.django_db
def test_clear_cache_deletes_statistics_keys(event):
    """clear_cache should delete statistics cache keys for the event."""
    event.cache.set("statistics_obd_data", "cached")
    event.cache.set("statistics_obp_data", "cached")
    event.cache.set("statistics_rev_data", "cached")
    clear_cache(event)
    assert event.cache.get("statistics_obd_data") is None
    assert event.cache.get("statistics_obp_data") is None
    assert event.cache.get("statistics_rev_data") is None
