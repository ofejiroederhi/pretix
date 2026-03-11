#
# Tests for the order-transaction dirty-tracking module (base/models/_transactions.py).
# Added to improve coverage of a high-risk financial path identified via coverage.xml.
#
from unittest.mock import patch

import pytest

from pretix.base.models._transactions import (
    DirtyTransactionsForOrderException, _check_for_dirty_orders, _fail,
    _transactions_mark_order_clean, dirty_transactions,
)

pytestmark = [pytest.mark.unit]


def test_transactions_mark_order_clean_removes_id():
    """_transactions_mark_order_clean removes the given order_id from the dirty set."""
    dirty_transactions.order_ids = {1, 2}
    _transactions_mark_order_clean(1)
    assert getattr(dirty_transactions, "order_ids", set()) == {2}


def test_transactions_mark_order_clean_idempotent_when_missing():
    """_transactions_mark_order_clean does not raise when order_id is not in the set."""
    dirty_transactions.order_ids = set()
    _transactions_mark_order_clean(999)
    assert dirty_transactions.order_ids == set()


def test_transactions_mark_order_clean_initializes_empty_set():
    """_transactions_mark_order_clean initializes order_ids when None."""
    if hasattr(dirty_transactions, "order_ids"):
        delattr(dirty_transactions, "order_ids")
    _transactions_mark_order_clean(1)
    assert getattr(dirty_transactions, "order_ids", None) is not None
    assert 1 not in dirty_transactions.order_ids


def test_fail_raises_when_fail_loudly_true():
    """_fail raises DirtyTransactionsForOrderException when fail_loudly is True."""
    with patch("pretix.base.models._transactions.fail_loudly", True):
        with pytest.raises(DirtyTransactionsForOrderException) as excinfo:
            _fail("test message")
        assert "test message" in str(excinfo.value)


def test_fail_logs_when_fail_loudly_false():
    """_fail logs and does not raise when fail_loudly is False."""
    with patch("pretix.base.models._transactions.fail_loudly", False):
        with patch("pretix.base.models._transactions.settings") as mock_settings:
            mock_settings.SENTRY_ENABLED = False
            with patch("pretix.base.models._transactions.logger") as mock_logger:
                _fail("test message")
                mock_logger.warning.assert_called_once()
                assert "test message" in mock_logger.warning.call_args[0][0]


def test_check_for_dirty_orders_empty_does_not_fail():
    """_check_for_dirty_orders with empty set does not call _fail."""
    dirty_transactions.order_ids = set()
    with patch("pretix.base.models._transactions._fail") as mock_fail:
        _check_for_dirty_orders()
        mock_fail.assert_not_called()
    assert getattr(dirty_transactions, "order_ids", set()) == set()


def test_check_for_dirty_orders_only_none_does_not_fail():
    """_check_for_dirty_orders with {None} does not call _fail."""
    dirty_transactions.order_ids = {None}
    with patch("pretix.base.models._transactions._fail") as mock_fail:
        _check_for_dirty_orders()
        mock_fail.assert_not_called()
    assert dirty_transactions.order_ids == set()


def test_check_for_dirty_orders_with_ids_calls_fail():
    """_check_for_dirty_orders with real order ids calls _fail and clears set."""
    dirty_transactions.order_ids = {1, 2}
    with patch("pretix.base.models._transactions._fail") as mock_fail:
        _check_for_dirty_orders()
        mock_fail.assert_called_once()
        assert "1" in mock_fail.call_args[0][0] or "2" in mock_fail.call_args[0][0]
    assert dirty_transactions.order_ids == set()


def test_check_for_dirty_orders_initializes_order_ids_when_none():
    """_check_for_dirty_orders initializes order_ids when None."""
    if hasattr(dirty_transactions, "order_ids"):
        delattr(dirty_transactions, "order_ids")
    with patch("pretix.base.models._transactions._fail"):
        _check_for_dirty_orders()
    assert getattr(dirty_transactions, "order_ids", None) is not None
    assert dirty_transactions.order_ids == set()
