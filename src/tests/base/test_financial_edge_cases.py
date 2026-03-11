#
# Risk-based tests for financial logic and data processing edge cases.
# Motivated by issue-tracker patterns: VAT/rounding defects, payment state consistency,
# bank import detection failures, and voucher/discount rounding.
#
from decimal import Decimal

import pytest
from django.conf import settings
from django.utils.timezone import now
from django_scopes import scopes_disabled

from pretix.base.decimal import round_decimal
from pretix.base.models import Event, Organizer, Voucher

pytestmark = [pytest.mark.unit]


@pytest.fixture
def event_eur():
    with scopes_disabled():
        o = Organizer.objects.create(name="Dummy", slug="dummy")
        e = Event.objects.create(
            organizer=o, name="Dummy", slug="dummy",
            currency="EUR",
            date_from=now(),
        )
        yield e


@pytest.fixture
def event_jpy():
    """Event with 0 decimal places (e.g. JPY) – boundary for rounding (issue-tracker: VAT rounding)."""
    with scopes_disabled():
        o = Organizer.objects.create(name="Dummy", slug="dummy")
        e = Event.objects.create(
            organizer=o, name="Dummy", slug="dummy",
            currency="JPY",
            date_from=now(),
        )
        yield e


# --- round_decimal / currency places (VAT rounding class of bugs) ---


@pytest.mark.django_db
def test_round_decimal_currency_three_places():
    """Round to 3 decimal places (e.g. KWD) – boundary for tax rounding."""
    places_dict = {**getattr(settings, 'CURRENCY_PLACES', {}), 'KWD': 3}
    result = round_decimal(Decimal("10.1255"), "KWD", places_dict=places_dict)
    assert result == Decimal("10.126")


@pytest.mark.django_db
def test_round_decimal_currency_zero_places():
    """Round to 0 decimal places (e.g. JPY) – avoids incorrect VAT rounding with fractional units."""
    places_dict = {**getattr(settings, 'CURRENCY_PLACES', {}), 'JPY': 0}
    result = round_decimal(Decimal("100.7"), "JPY", places_dict=places_dict)
    assert result == Decimal("101")


@pytest.mark.django_db
def test_round_decimal_no_currency_default_two_places():
    """When currency is None, round to default 2 decimal places (financial consistency)."""
    result = round_decimal(Decimal("10.1255"), None)
    assert result == Decimal("10.13")


@pytest.mark.django_db
def test_round_decimal_currency_eur_two_places():
    """EUR uses 2 decimal places (default for most currencies)."""
    places_dict = {**getattr(settings, 'CURRENCY_PLACES', {}), 'EUR': 2}
    result = round_decimal(Decimal("99.995"), "EUR", places_dict=places_dict)
    assert result == Decimal("100.00")


# --- Voucher calculate_price percent + currency places (financial logic) ---


@pytest.mark.django_db
def test_voucher_calculate_price_percent_eur_rounding(event_eur):
    """Voucher percent discount rounds correctly for 2-decimal currency (EUR)."""
    with scopes_disabled():
        v = Voucher.objects.create(
            event=event_eur,
            value=Decimal("33.33"),
            price_mode="percent",
        )
    # 100 * (100 - 33.33) / 100 = 66.67
    p = v.calculate_price(Decimal("100.00"))
    assert p == Decimal("66.67")


@pytest.mark.django_db
def test_voucher_calculate_price_percent_zero_places_currency(event_jpy):
    """Voucher percent discount with 0-decimal currency (JPY) quantizes to integer (issue-tracker: VAT/rounding)."""
    with scopes_disabled():
        v = Voucher.objects.create(
            event=event_jpy,
            value=Decimal("10"),
            price_mode="percent",
        )
    # 1000 * 0.9 = 900
    p = v.calculate_price(Decimal("1000"))
    assert p == Decimal("900")
    assert p == int(p)


@pytest.mark.django_db
def test_voucher_calculate_price_subtract_floor_zero(event_eur):
    """Voucher subtract mode: result never below zero (financial consistency)."""
    with scopes_disabled():
        v = Voucher.objects.create(
            event=event_eur,
            value=Decimal("50.00"),
            price_mode="subtract",
        )
    p = v.calculate_price(Decimal("30.00"))
    assert p == Decimal("0.00")
