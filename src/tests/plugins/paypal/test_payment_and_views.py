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
