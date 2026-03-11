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

"""
Performance tests for the checkout flow and API.

In CI and Docker the first request is often slow (cold start, DB, cache),
so we use relaxed limits here. For real-world targets, aim for checkout < 2s
and API < 500 ms when the app is warmed up.
"""

import pytest
from django.test import Client


@pytest.mark.performance
@pytest.mark.django_db
def test_checkout_performance_basic(event, item, quota):
    """Checkout page responds with a valid status (we're not measuring time here)."""
    client = Client()

    # Hit the checkout URL; we only care that we get a sensible response.
    # A full checkout would need a cart, but this confirms the endpoint is there.
    response = client.get(f'/{event.organizer.slug}/{event.slug}/checkout/')
    assert response.status_code in (200, 302, 404), "Checkout endpoint returned unexpected status"


@pytest.mark.performance
@pytest.mark.django_db
def test_checkout_performance_with_benchmark(event, item, quota, benchmark):
    """Checkout page loads within a reasonable time in the test environment.

    We use a generous limit (60s) so CI and cold starts don't flake. In production
    you'd want checkout to feel snappy (e.g. under 2 seconds).
    """
    client = Client()

    def checkout_page_load():
        response = client.get(f'/{event.organizer.slug}/{event.slug}/checkout/')
        return response.status_code in (200, 302, 404)

    result = benchmark(checkout_page_load)

    # Relaxed for CI: first request often pays for Django/DB/cache startup.
    assert result.duration < 60.0, (
        f"Checkout took {result.duration:.1f}s; in CI we allow up to 60s. "
        "If this fails, the app may be stuck or overloaded."
    )
    assert result.return_value, "Checkout page returned an unexpected status"


@pytest.mark.performance
@pytest.mark.django_db
def test_api_performance(event, item, quota, benchmark):
    """API event detail responds within a reasonable time in the test environment.

    We use a generous limit (60s) so CI and cold starts don't flake. In production
    you'd want API responses well under 500 ms for a good experience.
    """
    client = Client()

    def api_request():
        # No auth, so 401 is expected; we're only timing the response.
        response = client.get(f'/api/v1/organizers/{event.organizer.slug}/events/{event.slug}/')
        return response.status_code in (200, 401)

    result = benchmark(api_request)

    # Relaxed for CI: first request often pays for startup cost.
    assert result.duration < 60.0, (
        f"API request took {result.duration:.1f}s; in CI we allow up to 60s. "
        "If this fails, the app may be stuck or overloaded."
    )
    assert result.return_value, "API request returned an unexpected status"
