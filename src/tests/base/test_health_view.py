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
# Tests for the healthcheck view (base/views/health.py).
# Added to improve coverage of a high-risk reliability path identified via coverage.xml.
# Calls the view directly to avoid multidomain middleware (which expects orga, event, mode from cache).
#
from unittest.mock import patch

import pytest
from django.test import RequestFactory

from pretix.base.views.health import healthcheck

pytestmark = [pytest.mark.django_db, pytest.mark.unit]


def test_healthcheck_returns_200_when_db_and_cache_ok():
    """Health endpoint returns 200 when database and cache are available."""
    request = RequestFactory().get("/healthcheck/")
    with patch("pretix.base.views.health.cache.cache.get", return_value="1"):
        response = healthcheck(request)
    assert response.status_code == 200


def test_healthcheck_returns_503_when_cache_unavailable():
    """Health endpoint returns 503 when cache get does not return expected value."""
    request = RequestFactory().get("/healthcheck/")
    with patch("pretix.base.views.health.cache.cache.get", return_value=None):
        response = healthcheck(request)
    assert response.status_code == 503
    assert b"Cache not available" in response.content or b"not available" in response.content


def test_healthcheck_returns_503_when_cache_returns_wrong_value():
    """Health endpoint returns 503 when cache returns unexpected value."""
    request = RequestFactory().get("/healthcheck/")
    with patch("pretix.base.views.health.cache.cache.get", return_value="0"):
        response = healthcheck(request)
    assert response.status_code == 503
