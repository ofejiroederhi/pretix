#
# Unit tests for base/services/locking.py (pg_lock_key, KEY_SPACES, NoLockManager).
# Targets low-coverage concurrency/order-integrity paths.
#
import pytest
from django.utils.timezone import now
from django_scopes import scopes_disabled

from pretix.base.models import (
    Event, Item, ItemCategory, Organizer, Quota, Voucher,
)
from pretix.base.services.locking import KEY_SPACES, NoLockManager, pg_lock_key

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


@pytest.fixture
def event_and_quota():
    """Minimal event and quota for lock key tests."""
    with scopes_disabled():
        o = Organizer.objects.create(name="O", slug="o")
        e = Event.objects.create(organizer=o, name="E", slug="e", date_from=now())
        cat = ItemCategory.objects.create(event=e, name="C", position=0)
        item = Item.objects.create(event=e, name="I", category=cat, default_price=0)
        q = Quota.objects.create(event=e, name="Q", size=10)
        q.items.add(item)
        return e, q


def test_pg_lock_key_event(event_and_quota):
    """pg_lock_key returns an int for Event and is consistent for same pk."""
    event, _ = event_and_quota
    key = pg_lock_key(event)
    assert isinstance(key, int)
    assert pg_lock_key(event) == key
    assert KEY_SPACES[Event] == 1


def test_pg_lock_key_quota(event_and_quota):
    """pg_lock_key returns an int for Quota."""
    _, quota = event_and_quota
    key = pg_lock_key(quota)
    assert isinstance(key, int)
    assert KEY_SPACES[Quota] == 2


def test_pg_lock_key_voucher(event_and_quota):
    """pg_lock_key returns an int for Voucher."""
    event, _ = event_and_quota
    with scopes_disabled():
        v = Voucher.objects.create(event=event, code="LOCK")
    key = pg_lock_key(v)
    assert isinstance(key, int)
    assert KEY_SPACES[Voucher] == 4


def test_pg_lock_key_unknown_type_raises():
    """pg_lock_key raises ValueError for types without KEY_SPACES."""
    class UnknownModel:
        pk = 1
    obj = UnknownModel()
    with pytest.raises(ValueError) as exc_info:
        pg_lock_key(obj)
    assert "No key space defined" in str(exc_info.value)


def test_pg_lock_key_different_models_different_keys(event_and_quota):
    """Different model types with same pk produce different keys."""
    event, quota = event_and_quota
    # Event and Quota with pk=1 would be different objects; use same pk pattern
    assert pg_lock_key(event) != pg_lock_key(quota)


def test_no_lock_manager_context():
    """NoLockManager context manager returns a time and exits cleanly."""
    with NoLockManager() as t:
        assert t is not None
    # no exception on exit


def test_no_lock_manager_exit_propagates_exception():
    """NoLockManager does not suppress exceptions."""
    with pytest.raises(ValueError):
        with NoLockManager():
            raise ValueError("test")


def test_lock_objects_outside_atomic_raises(event_and_quota):
    """lock_objects raises RuntimeError when not in atomic block."""
    from unittest.mock import patch

    from pretix.base.services.locking import lock_objects
    _, quota = event_and_quota
    with patch("pretix.base.services.locking.connection") as mock_conn:
        mock_conn.in_atomic_block = False
        with pytest.raises(RuntimeError) as exc_info:
            lock_objects([quota])
        assert "transaction" in str(exc_info.value).lower()
