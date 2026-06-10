from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from worker.repositories.exchange_rate import ExchangeRateRepository


@pytest.fixture
def repo():
    return ExchangeRateRepository()


class TestSave:
    async def test_creates_and_inserts_exchange_rate(self, repo, usd_rate_data):
        with patch("worker.repositories.exchange_rate.ExchangeRate") as mock_cls:
            mock_rate = MagicMock()
            mock_rate.insert = AsyncMock()
            mock_cls.return_value = mock_rate

            result = await repo.save(usd_rate_data)

        mock_cls.assert_called_once_with(**usd_rate_data)
        mock_rate.insert.assert_called_once()
        assert result is mock_rate


class TestGetHistoricalAverage:
    def _patch_aggregate(self, return_value):
        mock_agg = MagicMock()
        mock_agg.to_list = AsyncMock(return_value=return_value)
        return patch("worker.repositories.exchange_rate.ExchangeRate.aggregate", return_value=mock_agg)

    async def test_empty_result_returns_none(self, repo):
        with self._patch_aggregate([]):
            result = await repo.get_historical_average("USD-BRL", 30)
        assert result is None

    async def test_fewer_than_10_samples_returns_none(self, repo):
        with self._patch_aggregate([{"average": 5.50, "count": 9}]):
            result = await repo.get_historical_average("USD-BRL", 30)
        assert result is None

    async def test_exactly_10_samples_returns_average(self, repo):
        with self._patch_aggregate([{"average": 5.50, "count": 10}]):
            result = await repo.get_historical_average("USD-BRL", 30)
        assert result == 5.50

    async def test_sufficient_samples_returns_average(self, repo):
        with self._patch_aggregate([{"average": 6.00, "count": 30}]):
            result = await repo.get_historical_average("EUR-BRL", 30)
        assert result == 6.00


class TestAlreadyNotifiedToday:
    async def test_returns_true_when_record_found(self, repo):
        with patch("worker.repositories.exchange_rate.ExchangeRate") as MockER:
            MockER.timestamp.__ge__.return_value = MagicMock()
            MockER.find_one = AsyncMock(return_value=MagicMock())
            result = await repo.already_notified_today("USD-BRL")
        assert result is True

    async def test_returns_false_when_no_record_found(self, repo):
        with patch("worker.repositories.exchange_rate.ExchangeRate") as MockER:
            MockER.timestamp.__ge__.return_value = MagicMock()
            MockER.find_one = AsyncMock(return_value=None)
            result = await repo.already_notified_today("USD-BRL")
        assert result is False


class TestMarkAsNotified:
    async def test_sets_notified_true_and_saves(self, repo):
        mock_rate = MagicMock()
        mock_rate.save = AsyncMock()

        await repo.mark_as_notified(mock_rate)

        assert mock_rate.notified is True
        mock_rate.save.assert_called_once()
