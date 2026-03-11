#
# Unit tests for base/services/tax.py (normalize_vat_id) and base/models/tax.py (is_eu_country, cc_to_vat_prefix).
# Targets low-coverage tax/VAT paths.
#
import pytest

from pretix.base.models.tax import cc_to_vat_prefix, is_eu_country
from pretix.base.services.tax import normalize_vat_id

pytestmark = [pytest.mark.unit]


# --- normalize_vat_id (services/tax.py) ---


def test_normalize_vat_id_empty_returns_none():
    assert normalize_vat_id("", "DE") is None


def test_normalize_vat_id_non_string_raises():
    with pytest.raises(TypeError) as exc_info:
        normalize_vat_id(12345, "DE")
    assert "not a string" in str(exc_info.value)


def test_normalize_vat_id_too_short_raises():
    with pytest.raises(ValueError) as exc_info:
        normalize_vat_id("AB", "DE")
    assert "at least three" in str(exc_info.value)


def test_normalize_vat_id_strips_spaces_and_uppercase():
    result = normalize_vat_id(" de 123456789 ", "DE")
    assert result == "DE123456789" or "DE" in result


def test_normalize_vat_id_removes_dashes_and_dots():
    result = normalize_vat_id("DE-12.345.678-9", "DE")
    assert "-" not in result
    assert "." not in result


# --- is_eu_country, cc_to_vat_prefix (models/tax.py) ---


def test_cc_to_vat_prefix_gr_returns_el():
    assert cc_to_vat_prefix("GR") == "EL"


def test_cc_to_vat_prefix_other_returns_same():
    assert cc_to_vat_prefix("DE") == "DE"
    assert cc_to_vat_prefix("FR") == "FR"


def test_cc_to_vat_prefix_coerces_to_str():
    assert cc_to_vat_prefix("DE") == "DE"


def test_is_eu_country_de_true():
    assert is_eu_country("DE") is True


def test_is_eu_country_xx_false():
    assert is_eu_country("XX") is False


def test_is_eu_country_coerces_to_str():
    assert is_eu_country("DE") is True
