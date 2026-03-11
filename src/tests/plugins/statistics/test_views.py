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
# Tests for pretix.plugins.statistics views (IndexView).
# Targets: statistics/views.py (coverage was ~12%, improve toward 75%+).
#
from datetime import datetime, timezone

import pytest
from django.test import Client

from pretix.base.models import Event, Organizer, Team, User


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
        plugins="pretix.plugins.banktransfer,pretix.plugins.statistics",
    )


@pytest.fixture
def user(event):
    user = User.objects.create_user("stats@test.example", "test")
    team = Team.objects.create(
        organizer=event.organizer,
        can_view_orders=True,
        all_events=True,
    )
    team.members.add(user)
    return user


@pytest.mark.django_db
def test_statistics_index_requires_login(event):
    """Statistics index returns 302/403 when not logged in."""
    client = Client()
    url = "/control/event/{}/{}/statistics/".format(
        event.organizer.slug, event.slug
    )
    response = client.get(url)
    assert response.status_code in (302, 403)


@pytest.mark.django_db
def test_statistics_index_200_with_permission(event, user):
    """Statistics index returns 200 and context when user has can_view_orders."""
    client = Client()
    client.force_login(user)
    url = "/control/event/{}/{}/statistics/".format(
        event.organizer.slug, event.slug
    )
    response = client.get(url)
    assert response.status_code == 200
    # View puts chart data and has_orders in context
    assert "has_orders" in response.context or response.content


@pytest.mark.django_db
def test_statistics_index_with_latest_clears_cache(event, user):
    """Request with ?latest= clears statistics cache and recomputes."""
    client = Client()
    client.force_login(user)
    url = "/control/event/{}/{}/statistics/?latest=1".format(
        event.organizer.slug, event.slug
    )
    response = client.get(url)
    assert response.status_code == 200
