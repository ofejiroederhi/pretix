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
# Unit tests for base/services/stats.py (tuplesum, dictsum, Dontsum).
# Targets low-coverage stats/aggregation paths.
#
import pytest

from pretix.base.services.stats import Dontsum, dictsum, tuplesum

pytestmark = [pytest.mark.unit]


def test_tuplesum_simple():
    """tuplesum sums each component of tuples."""
    result = tuplesum([(1, 2), (3, 4), (5, 6)])
    assert result == (9, 12)


def test_tuplesum_single_tuple():
    """tuplesum with one tuple returns that tuple."""
    result = tuplesum([(10, 20)])
    assert result == (10, 20)


def test_tuplesum_ignores_dontsum():
    """tuplesum ignores Dontsum values in each position."""
    result = tuplesum([(1, 2), (Dontsum(99), 4), (5, 6)])
    # First component: 1 + 5 (Dontsum ignored) = 6; second: 2 + 4 + 6 = 12
    assert result == (6, 12)


def test_tuplesum_triples():
    """tuplesum works with tuples of size 3."""
    result = tuplesum([(1, 2, 3), (4, 5, 6)])
    assert result == (5, 7, 9)


def test_dontsum_str():
    """Dontsum value stringifies to wrapped value."""
    d = Dontsum(42)
    assert str(d) == "42"


def test_dictsum_two_dicts():
    """dictsum merges two dicts and sums tuple values per key."""
    result = dictsum({"a": (1, 2), "b": (3, 4)}, {"a": (5, 6), "c": (7, 8)})
    assert result == {"a": (6, 8), "b": (3, 4), "c": (7, 8)}


def test_dictsum_single_dict():
    """dictsum with one dict returns equivalent."""
    result = dictsum({"x": (1, 2)})
    assert result == {"x": (1, 2)}


def test_dictsum_empty():
    """dictsum with no dicts returns empty."""
    result = dictsum()
    assert result == {}
