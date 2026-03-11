#
# Unit tests for base/validators.py (reserved slugs, email, rrule validation).
# Targets low-coverage, high-risk input-validation paths.
#
import pytest
from django.conf import settings
from django.core.exceptions import ValidationError

from pretix.base.validators import (
    BanlistValidator, EmailBanlistValidator, EventSlugBanlistValidator,
    OrganizerSlugBanlistValidator, RRuleValidator, multimail_validate,
)

pytestmark = [pytest.mark.unit]


# --- BanlistValidator / EventSlugBanlistValidator ---


def test_event_slug_banlist_rejects_reserved_slug():
    validator = EventSlugBanlistValidator()
    with pytest.raises(ValidationError) as exc_info:
        validator("control")
    assert exc_info.value.code == "invalid"
    assert "control" in str(exc_info.value)


def test_event_slug_banlist_rejects_healthcheck():
    validator = EventSlugBanlistValidator()
    with pytest.raises(ValidationError):
        validator("healthcheck")


def test_event_slug_banlist_accepts_valid_slug():
    validator = EventSlugBanlistValidator()
    validator("my-event-2024")


# --- OrganizerSlugBanlistValidator ---


def test_organizer_slug_banlist_rejects_reserved_slug():
    validator = OrganizerSlugBanlistValidator()
    with pytest.raises(ValidationError) as exc_info:
        validator("api")
    assert exc_info.value.code == "invalid"


def test_organizer_slug_banlist_accepts_valid_slug():
    validator = OrganizerSlugBanlistValidator()
    validator("my-org")


# --- EmailBanlistValidator ---


def test_email_banlist_rejects_none_value():
    validator = EmailBanlistValidator()
    with pytest.raises(ValidationError):
        validator(settings.PRETIX_EMAIL_NONE_VALUE)


def test_email_banlist_accepts_normal_email():
    validator = EmailBanlistValidator()
    validator("user@example.com")


# --- multimail_validate ---


def test_multimail_validate_single_email():
    result = multimail_validate("user@example.com")
    assert result == ["user@example.com"]


def test_multimail_validate_multiple_emails():
    """multimail_validate validates each part (after strip) but returns split list as-is."""
    result = multimail_validate("a@x.com, b@y.com")
    assert result == ["a@x.com", " b@y.com"]


def test_multimail_validate_invalid_raises():
    with pytest.raises(ValidationError):
        multimail_validate("not-an-email")


# --- RRuleValidator (no enforce_simple) ---


def test_rrule_validator_accepts_valid_rrule():
    validator = RRuleValidator(enforce_simple=False)
    validator("FREQ=DAILY;COUNT=5")


def test_rrule_validator_rejects_invalid_rrule():
    validator = RRuleValidator(enforce_simple=False)
    with pytest.raises(ValidationError) as exc_info:
        validator("NOT-A-RRULE")
    assert "Not a valid rrule" in str(exc_info.value)


# --- RRuleValidator (enforce_simple=True) ---


def test_rrule_validator_enforce_simple_accepts_daily():
    validator = RRuleValidator(enforce_simple=True)
    validator("FREQ=DAILY;COUNT=3")


def test_rrule_validator_enforce_simple_unsupported_freq():
    validator = RRuleValidator(enforce_simple=True)
    with pytest.raises(ValidationError) as exc_info:
        validator("FREQ=HOURLY;COUNT=1")
    assert "Unsupported FREQ" in str(exc_info.value)


def test_rrule_validator_enforce_simple_bymonthday_not_supported():
    validator = RRuleValidator(enforce_simple=True)
    with pytest.raises(ValidationError) as exc_info:
        validator("FREQ=MONTHLY;BYMONTHDAY=15;COUNT=1")
    assert "BYMONTHDAY" in str(exc_info.value)


def test_rrule_validator_enforce_simple_byyearday_not_supported():
    validator = RRuleValidator(enforce_simple=True)
    with pytest.raises(ValidationError) as exc_info:
        validator("FREQ=YEARLY;BYYEARDAY=1;COUNT=1")
    assert "BYYEARDAY" in str(exc_info.value)


def test_rrule_validator_enforce_simple_only_single_rrule():
    # rrulestr can return rruleset for combined rules
    validator = RRuleValidator(enforce_simple=True)
    with pytest.raises(ValidationError) as exc_info:
        validator("FREQ=DAILY;COUNT=1;DTSTART=20240101T120000Z\nFREQ=WEEKLY;COUNT=1;DTSTART=20240101T120000Z")
    assert "single RRULE" in str(exc_info.value) or "Not a valid" in str(exc_info.value)


# --- BanlistValidator base (empty banlist) ---


def test_banlist_validator_empty_accepts_any():
    validator = BanlistValidator()
    validator("anything")
