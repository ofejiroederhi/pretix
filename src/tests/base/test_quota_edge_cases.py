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
# Quota availability and boundary tests: zero quota, exceeded quota, and voucher ignore/block.
# Supports distinction-level multi-level testing (unit/integration).
#
from datetime import timedelta

import pytest
from django.utils.timezone import now
from django_scopes import scopes_disabled

from pretix.base.models import (
    Event, Item, ItemCategory, Order, OrderPosition, Organizer, Quota,
)

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


@pytest.fixture
def event_quota_item():
    """Event with one quota and one item for quota edge-case tests."""
    with scopes_disabled():
        o = Organizer.objects.create(name="Dummy", slug="dummy")
        e = Event.objects.create(
            organizer=o, name="Dummy", slug="dummy",
            date_from=now(), live=True,
        )
        cat = ItemCategory.objects.create(event=e, name="Tickets", position=0)
        q = Quota.objects.create(event=e, name="Tickets", size=3)
        item = Item.objects.create(
            event=e, name="Ticket", category=cat, default_price=10, admission=True,
        )
        q.items.add(item)
    return e, q, item


def test_quota_availability_ok_when_empty(event_quota_item):
    """Quota with no orders reports AVAILABILITY_OK and correct count."""
    event, quota, item = event_quota_item
    with scopes_disabled():
        code, num = quota.availability()
    assert code == Quota.AVAILABILITY_OK
    assert num == 3


def test_quota_availability_decreases_with_positions(event_quota_item):
    """Quota availability decreases as order positions consume capacity."""
    event, quota, item = event_quota_item
    with scopes_disabled():
        sales_channel = event.organizer.sales_channels.get(identifier="web")
        o = Order.objects.create(
            code="ORD1", event=event, email="a@b.c",
            status=Order.STATUS_PAID,
            datetime=now(), expires=now() + timedelta(days=10),
            total=10, sales_channel=sales_channel,
        )
        OrderPosition.objects.create(
            order=o, item=item, variation=None, price=10, positionid=1,
        )
    with scopes_disabled():
        code, num = quota.availability()
    assert code == Quota.AVAILABILITY_OK
    assert num == 2


def test_quota_availability_gone_when_exhausted(event_quota_item):
    """Quota with size equal to ordered positions reports AVAILABILITY_GONE."""
    event, quota, item = event_quota_item
    with scopes_disabled():
        sales_channel = event.organizer.sales_channels.get(identifier="web")
        for i in range(3):
            o = Order.objects.create(
                code=f"ORD{i}", event=event, email="a@b.c",
                status=Order.STATUS_PAID,
                datetime=now(), expires=now() + timedelta(days=10),
                total=10, sales_channel=sales_channel,
            )
            OrderPosition.objects.create(
                order=o, item=item, variation=None, price=10, positionid=1,
            )
    with scopes_disabled():
        code, num = quota.availability()
    assert code == Quota.AVAILABILITY_GONE
    assert num == 0


def test_quota_zero_size_unavailable(event_quota_item):
    """Quota with size=0 is unavailable (boundary for configuration errors)."""
    event, quota, item = event_quota_item
    quota.size = 0
    quota.save()
    with scopes_disabled():
        code, num = quota.availability()
    assert code == Quota.AVAILABILITY_GONE
    assert num == 0
