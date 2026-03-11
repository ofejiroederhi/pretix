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
# Performance / load tests: quota contention under concurrent ticket purchases.
# Ensures that under quota=1 only one order succeeds when multiple requests run in parallel.
# Run with: pytest tests/concurrency_tests/test_quota_contention_performance.py -m performance --reuse-db
#
import asyncio

import pytest
from asgiref.sync import sync_to_async
from django.conf import settings
from django_scopes import scopes_disabled
from tests.concurrency_tests.utils import post

from pretix.base.models import CartPosition, OrderPosition


@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.slow
async def test_concurrent_purchases_under_quota_only_one_succeeds(
    live_server, session, event, item, quota, cart1_expired, cart2_expired
):
    """
    Under quota=1, two concurrent checkout confirmations result in exactly one order.
    Documents quota contention behaviour for performance and correctness.
    """
    quota.size = 1
    await sync_to_async(quota.save)()

    url = (
        f"/{event.organizer.slug}/{event.slug}/checkout/confirm/"
        f"?_debug_flag=skip-csrf&_debug_flag=sleep-after-quota-check"
    )
    payload = {}

    r1, r2 = await asyncio.gather(
        post(
            session,
            f"{live_server}{url}",
            data=payload,
            cookies={settings.SESSION_COOKIE_NAME: cart1_expired[1].session_key},
        ),
        post(
            session,
            f"{live_server}{url}",
            data=payload,
            cookies={settings.SESSION_COOKIE_NAME: cart2_expired[1].session_key},
        ),
    )
    success_count = ['thank-you' in r1, 'thank-you' in r2].count(True)
    assert success_count == 1, "Exactly one checkout should succeed when quota=1"

    with scopes_disabled():

        def _count():
            return OrderPosition.objects.filter(item=item).count()

        order_count = await sync_to_async(_count)()
        assert order_count == 1
        assert await sync_to_async(CartPosition.objects.filter(item=item).count)() == 0
