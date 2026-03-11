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
# End-to-end workflow tests: full checkout flow, voucher redemption, and payment consistency.
# These tests exercise multiple components (presale, cart, order, payment) together.
#
import datetime
from decimal import Decimal
from unittest import mock

import pytest
from bs4 import BeautifulSoup
from django.test import Client
from django.utils.timezone import now
from django_scopes import scopes_disabled

from pretix.base.models import (
    CartPosition, Event, Item, ItemCategory, Order, OrderPosition, Organizer,
    Quota, Voucher,
)
from pretix.base.services.orders import _perform_order
from pretix.testutils.sessions import get_cart_session_key

pytestmark = [pytest.mark.django_db, pytest.mark.integration, pytest.mark.e2e]


@pytest.fixture
def checkout_env():
    """Minimal event + quota + item for E2E checkout (free order)."""
    with scopes_disabled():
        orga = Organizer.objects.create(
            name="E2E", slug="e2e",
            plugins="pretix.plugins.banktransfer,tests.testdummy",
        )
        event = Event.objects.create(
            organizer=orga, name="E2E Event", slug="e2e",
            date_from=datetime.datetime(now().year + 1, 12, 26, tzinfo=datetime.timezone.utc),
            plugins="pretix.plugins.banktransfer,tests.testdummy",
            live=True,
        )
        event.tax_rules.create(rate=0, default=True)
        event.settings.set("timezone", "UTC")
        event.settings.set("attendee_names_asked", False)
        event.settings.set("payment_banktransfer__enabled", True)
        cat = ItemCategory.objects.create(event=event, name="Tickets", position=0)
        quota = Quota.objects.create(event=event, name="Tickets", size=10)
        item = Item.objects.create(
            event=event, name="Free ticket", category=cat, default_price=0,
            admission=True, tax_rule=event.tax_rules.get(default=True),
        )
        quota.items.add(item)
    return orga, event, quota, item


@pytest.fixture
def client_with_cart(checkout_env):
    """Django test client with session and cart initialized for event."""
    orga, event, quota, item = checkout_env
    client = Client()
    client.get("/%s/%s/" % (orga.slug, event.slug))
    return client, orga, event, quota, item


def _set_session(client, event, key, value):
    session = client.session
    sk = get_cart_session_key(client, event)
    session["carts"][sk][key] = value
    session.save()


def _set_payment(client, event):
    _set_session(client, event, "payments", [{
        "id": "test1",
        "provider": "banktransfer",
        "max_value": None,
        "min_value": None,
        "multi_use_supported": False,
        "info_data": {},
    }])


def test_full_checkout_creates_order(client_with_cart):
    """E2E: Add free item to cart, confirm checkout; assert one order created and PAID."""
    client, orga, event, quota, item = client_with_cart
    session_key = get_cart_session_key(client, event)
    with scopes_disabled():
        CartPosition.objects.create(
            event=event, cart_id=session_key, item=item,
            price=0, listed_price=0, price_after_voucher=0,
            expires=now() + datetime.timedelta(minutes=10),
        )
    _set_payment(client, event)
    _set_session(client, event, "email", "user@example.com")
    with mock.patch("django.db.transaction.on_commit", lambda t: t()):
        response = client.post(
            "/%s/%s/checkout/confirm/" % (orga.slug, event.slug),
            follow=True,
        )
    doc = BeautifulSoup(response.content.decode(), "lxml")
    assert len(doc.select(".thank-you")) == 1
    with scopes_disabled():
        assert not CartPosition.objects.filter(cart_id=session_key).exists()
        assert Order.objects.filter(event=event).count() == 1
        order = Order.objects.get(event=event)
        assert order.status == Order.STATUS_PAID
        assert OrderPosition.objects.filter(order=order).count() == 1
        assert OrderPosition.objects.get(order=order).price == 0


def test_voucher_multi_use_two_orders(checkout_env):
    """Integration: Multi-use voucher applied to two separate orders; usage count and totals correct."""
    orga, event, quota, item = checkout_env
    with scopes_disabled():
        # Add a paid item for voucher discount
        item_paid = Item.objects.create(
            event=event, name="Paid ticket", category=item.category,
            default_price=Decimal("10.00"), admission=True,
            tax_rule=event.tax_rules.get(default=True),
        )
        quota.items.add(item_paid)
        voucher = Voucher.objects.create(
            event=event,
            code="MULTI10",
            value=Decimal("5.00"),
            price_mode="subtract",
            max_usages=5,
            redeemed=0,
        )
        manual_payment = [{
            "id": "m1",
            "provider": "manual",
            "max_value": None,
            "min_value": None,
            "multi_use_supported": False,
            "info_data": {},
        }]
    # First order: one position at 10, voucher subtracts 5 -> 5
    with scopes_disabled():
        cp1 = CartPosition.objects.create(
            event=event, cart_id="cart1", item=item_paid,
            price=Decimal("5.00"),  # after voucher
            listed_price=Decimal("10.00"),
            price_after_voucher=Decimal("5.00"),
            voucher=voucher,
            expires=now() + datetime.timedelta(minutes=10),
        )
    with scopes_disabled():
        with mock.patch("django.db.transaction.on_commit", lambda t: t()):
            _perform_order(event, manual_payment, [cp1.pk], "user1@test.com", "en", None, {}, "web")
    with scopes_disabled():
        voucher.refresh_from_db()
        assert voucher.redeemed == 1
        assert Order.objects.filter(event=event).count() == 1
        assert Order.objects.get(event=event).total == Decimal("5.00")
    # Second order: same voucher
    with scopes_disabled():
        cp2 = CartPosition.objects.create(
            event=event, cart_id="cart2", item=item_paid,
            price=Decimal("5.00"),
            listed_price=Decimal("10.00"),
            price_after_voucher=Decimal("5.00"),
            voucher=voucher,
            expires=now() + datetime.timedelta(minutes=10),
        )
    with scopes_disabled():
        with mock.patch("django.db.transaction.on_commit", lambda t: t()):
            _perform_order(event, manual_payment, [cp2.pk], "user2@test.com", "en", None, {}, "web")
    with scopes_disabled():
        voucher.refresh_from_db()
        assert voucher.redeemed == 2
        assert Order.objects.filter(event=event).count() == 2
