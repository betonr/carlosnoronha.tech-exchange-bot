from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from core.models import ExchangeRate


@pytest.fixture(autouse=True)
def mock_beanie_init():
    """Beanie requires init_beanie() before instantiating Documents. Mock it for unit tests."""
    with patch.object(ExchangeRate, "get_motor_collection", return_value=MagicMock()):
        yield


def test_exchange_rate_field_values():
    rate = ExchangeRate(
        pair="USD-BRL",
        bid=5.50,
        ask=5.55,
        high=5.60,
        low=5.45,
        change_pct=0.5,
    )
    assert rate.pair == "USD-BRL"
    assert rate.bid == 5.50
    assert rate.ask == 5.55
    assert rate.high == 5.60
    assert rate.low == 5.45
    assert rate.change_pct == 0.5


def test_notified_defaults_to_false():
    rate = ExchangeRate(pair="USD-BRL", bid=5.5, ask=5.55, high=5.6, low=5.45, change_pct=0.5)
    assert rate.notified is False


def test_timestamp_is_timezone_aware():
    rate = ExchangeRate(pair="USD-BRL", bid=5.5, ask=5.55, high=5.6, low=5.45, change_pct=0.5)
    assert isinstance(rate.timestamp, datetime)
    assert rate.timestamp.tzinfo is not None


def test_notified_can_be_set_true():
    rate = ExchangeRate(pair="EUR-BRL", bid=6.0, ask=6.05, high=6.1, low=5.95, change_pct=-0.3, notified=True)
    assert rate.notified is True
