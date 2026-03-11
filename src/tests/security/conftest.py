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
