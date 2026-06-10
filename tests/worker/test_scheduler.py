from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from worker.repositories.exchange_rate import ExchangeRateRepository
from worker.scheduler import Scheduler
from worker.services.email import EmailService
from worker.services.exchange_api import ExchangeApiService


@pytest.fixture
def scheduler(settings):
    sched = Scheduler(settings)
    sched._api = MagicMock(spec=ExchangeApiService)
    sched._email = MagicMock(spec=EmailService)
    sched._repo = MagicMock(spec=ExchangeRateRepository)
    sched._repo.save = AsyncMock(return_value=MagicMock())
    sched._repo.already_notified_today = AsyncMock(return_value=False)
    sched._repo.get_historical_average = AsyncMock(return_value=None)
    sched._repo.mark_as_notified = AsyncMock()
    return sched


class TestWithinWindow:
    def _set_hour(self, hour):
        mock = MagicMock()
        mock.now.return_value.hour = hour
        return patch("worker.scheduler.datetime", mock)

    def test_inside_window_returns_true(self, scheduler):
        with self._set_hour(12):
            assert scheduler._within_window() is True

    def test_at_window_start_returns_true(self, scheduler):
        with self._set_hour(scheduler._settings.window_start):
            assert scheduler._within_window() is True

    def test_before_window_start_returns_false(self, scheduler):
        with self._set_hour(scheduler._settings.window_start - 1):
            assert scheduler._within_window() is False

    def test_at_window_end_returns_false(self, scheduler):
        with self._set_hour(scheduler._settings.window_end):
            assert scheduler._within_window() is False

    def test_after_window_end_returns_false(self, scheduler):
        with self._set_hour(scheduler._settings.window_end + 1):
            assert scheduler._within_window() is False


class TestRunCycle:
    async def test_skips_outside_operating_window(self, scheduler):
        with patch.object(scheduler, "_within_window", return_value=False):
            await scheduler._run_cycle()
        scheduler._api.fetch_rates.assert_not_called()

    async def test_aborts_when_fetch_returns_none(self, scheduler):
        with patch.object(scheduler, "_within_window", return_value=True):
            scheduler._api.fetch_rates.return_value = None
            await scheduler._run_cycle()
        scheduler._repo.save.assert_not_called()

    async def test_skips_pair_already_notified_today(self, scheduler, usd_rate_data):
        with patch.object(scheduler, "_within_window", return_value=True):
            scheduler._api.fetch_rates.return_value = [usd_rate_data]
            scheduler._repo.already_notified_today = AsyncMock(return_value=True)
            await scheduler._run_cycle()
        scheduler._api.should_notify.assert_not_called()
        scheduler._email.send_alert.assert_not_called()

    async def test_sends_alert_and_marks_notified(self, scheduler, usd_rate_data):
        with patch.object(scheduler, "_within_window", return_value=True):
            scheduler._api.fetch_rates.return_value = [usd_rate_data]
            scheduler._api.should_notify.return_value = (True, "above threshold")
            await scheduler._run_cycle()
        scheduler._email.send_alert.assert_called_once_with(usd_rate_data, "above threshold")
        scheduler._repo.mark_as_notified.assert_called_once()

    async def test_email_failure_does_not_mark_notified(self, scheduler, usd_rate_data):
        with patch.object(scheduler, "_within_window", return_value=True):
            scheduler._api.fetch_rates.return_value = [usd_rate_data]
            scheduler._api.should_notify.return_value = (True, "above threshold")
            scheduler._email.send_alert.side_effect = Exception("SMTP failure")
            await scheduler._run_cycle()
        scheduler._repo.mark_as_notified.assert_not_called()

    async def test_no_alert_condition_does_not_send_email(self, scheduler, usd_rate_data):
        with patch.object(scheduler, "_within_window", return_value=True):
            scheduler._api.fetch_rates.return_value = [usd_rate_data]
            scheduler._api.should_notify.return_value = (False, "")
            await scheduler._run_cycle()
        scheduler._email.send_alert.assert_not_called()
        scheduler._repo.mark_as_notified.assert_not_called()

    async def test_processes_multiple_pairs(self, scheduler, usd_rate_data):
        eur_rate_data = {**usd_rate_data, "pair": "EUR-BRL", "bid": 6.00}
        with patch.object(scheduler, "_within_window", return_value=True):
            scheduler._api.fetch_rates.return_value = [usd_rate_data, eur_rate_data]
            scheduler._api.should_notify.return_value = (False, "")
            await scheduler._run_cycle()
        assert scheduler._repo.save.call_count == 2
