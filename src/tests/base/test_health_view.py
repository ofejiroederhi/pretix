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
