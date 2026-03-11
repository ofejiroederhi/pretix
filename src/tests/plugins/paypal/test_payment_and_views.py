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
# Tests for pretix.plugins.paypal payment provider and views.
# Targets: payment.py (identifier, settings), views.py (redirect_view).
#
import pytest
from django.utils.timezone import now

from pretix.base.models import Event, Organizer
from pretix.plugins.paypal.payment import Paypal


@pytest.fixture
def event():
    o = Organizer.objects.create(name="Dummy", slug="dummy")
    return Event.objects.create(
        organizer=o,
        name="Dummy",
        slug="dummy",
        plugins="pretix.plugins.paypal",
        date_from=now(),
    )


@pytest.mark.django_db
def test_paypal_provider_identifier_and_verbose_name(event):
    """PayPal provider has correct identifier and verbose_name."""
    prov = Paypal(event)
    assert prov.identifier == "paypal"
    assert "paypal" in str(prov.verbose_name).lower()


@pytest.mark.django_db
def test_paypal_payment_form_fields_empty(event):
    """PayPal has no extra payment form fields (all via redirect)."""
    prov = Paypal(event)
    assert isinstance(prov.payment_form_fields, dict)
    assert len(prov.payment_form_fields) == 0


@pytest.mark.django_db
def test_paypal_redirect_view_bad_signature(event):
    """redirect_view returns 400 when url signature is invalid."""
    from django.test import RequestFactory

    from pretix.plugins.paypal.views import redirect_view

    factory = RequestFactory()
    request = factory.get("/paypal/redirect/", {"url": "invalid-signature"})
    request.event = event
    response = redirect_view(request, organizer=event.organizer.slug, event=event.slug)
    assert response.status_code == 400
    assert "Invalid" in response.content.decode()
