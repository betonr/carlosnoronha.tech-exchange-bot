from unittest.mock import MagicMock, patch

import pytest
import requests

from worker.services.exchange_api import ExchangeApiService

MOCK_API_RESPONSE = {
    "USDBRL": {
        "bid": "5.50",
        "ask": "5.55",
        "high": "5.60",
        "low": "5.45",
        "pctChange": "0.5",
    },
    "EURBRL": {
        "bid": "6.00",
        "ask": "6.05",
        "high": "6.10",
        "low": "5.95",
        "pctChange": "0.3",
    },
}


@pytest.fixture
def api_service(settings):
    return ExchangeApiService(settings)


def _mock_get(response_data):
    mock_resp = MagicMock()
    mock_resp.json.return_value = response_data
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


class TestFetchRates:
    def test_returns_both_pairs_on_success(self, api_service):
        with patch("worker.services.exchange_api.requests.get", return_value=_mock_get(MOCK_API_RESPONSE)):
            rates = api_service.fetch_rates()

        assert rates is not None
        assert len(rates) == 2
        pairs = {r["pair"] for r in rates}
        assert pairs == {"USD-BRL", "EUR-BRL"}

    def test_parses_rate_fields_correctly(self, api_service):
        with patch("worker.services.exchange_api.requests.get", return_value=_mock_get(MOCK_API_RESPONSE)):
            rates = api_service.fetch_rates()

        usd = next(r for r in rates if r["pair"] == "USD-BRL")
        assert usd["bid"] == 5.50
        assert usd["ask"] == 5.55
        assert usd["high"] == 5.60
        assert usd["low"] == 5.45
        assert usd["change_pct"] == 0.5

    def test_http_error_returns_none(self, api_service):
        with patch(
            "worker.services.exchange_api.requests.get",
            side_effect=requests.RequestException("timeout"),
        ):
            result = api_service.fetch_rates()

        assert result is None

    def test_missing_pair_is_skipped(self, api_service):
        partial = {"USDBRL": MOCK_API_RESPONSE["USDBRL"]}
        with patch("worker.services.exchange_api.requests.get", return_value=_mock_get(partial)):
            rates = api_service.fetch_rates()

        assert rates is not None
        assert len(rates) == 1
        assert rates[0]["pair"] == "USD-BRL"

    def test_all_pairs_missing_returns_none(self, api_service):
        with patch("worker.services.exchange_api.requests.get", return_value=_mock_get({})):
            result = api_service.fetch_rates()

        assert result is None

    def test_no_api_key_sends_empty_params(self, api_service):
        api_service._api_key = ""
        with patch("worker.services.exchange_api.requests.get", return_value=_mock_get(MOCK_API_RESPONSE)) as mock_get:
            api_service.fetch_rates()

        _, kwargs = mock_get.call_args
        assert kwargs["params"] == {}

    def test_api_key_included_as_token_param(self, api_service):
        api_service._api_key = "mytoken"
        with patch("worker.services.exchange_api.requests.get", return_value=_mock_get(MOCK_API_RESPONSE)) as mock_get:
            api_service.fetch_rates()

        _, kwargs = mock_get.call_args
        assert kwargs["params"] == {"token": "mytoken"}


class TestShouldNotify:
    def test_above_usd_threshold_triggers_alert(self, api_service, settings):
        notify, reason = api_service.should_notify("USD-BRL", settings.threshold_usd + 0.01, None)
        assert notify is True
        assert "threshold" in reason

    def test_at_usd_threshold_triggers_alert(self, api_service, settings):
        notify, _ = api_service.should_notify("USD-BRL", settings.threshold_usd, None)
        assert notify is True

    def test_below_usd_threshold_no_avg_no_alert(self, api_service, settings):
        notify, _ = api_service.should_notify("USD-BRL", settings.threshold_usd - 0.01, None)
        assert notify is False

    def test_above_eur_threshold_triggers_alert(self, api_service, settings):
        notify, reason = api_service.should_notify("EUR-BRL", settings.threshold_eur + 0.01, None)
        assert notify is True
        assert "threshold" in reason

    def test_above_historical_average_triggers_alert(self, api_service, settings):
        avg = 5.00
        limit = avg * (1 + settings.average_percent_above / 100)
        notify, reason = api_service.should_notify("USD-BRL", limit, avg)
        assert notify is True
        assert "average" in reason

    def test_below_historical_average_no_alert(self, api_service, settings):
        avg = 5.00
        limit = avg * (1 + settings.average_percent_above / 100)
        notify, _ = api_service.should_notify("USD-BRL", limit - 0.01, avg)
        assert notify is False

    def test_reason_includes_threshold_value(self, api_service, settings):
        _, reason = api_service.should_notify("USD-BRL", settings.threshold_usd, None)
        assert str(settings.threshold_usd) in reason

    def test_reason_includes_average_value(self, api_service, settings):
        avg = 5.00
        limit = avg * (1 + settings.average_percent_above / 100)
        _, reason = api_service.should_notify("USD-BRL", limit, avg)
        assert f"{avg:.4f}" in reason
