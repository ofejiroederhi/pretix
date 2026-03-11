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
