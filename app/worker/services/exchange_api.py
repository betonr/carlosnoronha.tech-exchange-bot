import logging

import requests

from core.config import Settings

logger = logging.getLogger(__name__)

PAIRS = ["USD-BRL", "EUR-BRL"]
API_BASE = "https://economia.awesomeapi.com.br/json/last"


class ExchangeApiService:
    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.awesomeapi_key
        self._threshold = {
            "USD-BRL": settings.threshold_usd,
            "EUR-BRL": settings.threshold_eur,
        }
        self._average_days = settings.average_days
        self._average_percent_above = settings.average_percent_above

    def fetch_rates(self) -> list[dict] | None:
        url = f"{API_BASE}/{','.join(PAIRS)}"
        params = {"token": self._api_key} if self._api_key else {}
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.error("Failed to fetch rates from AwesomeAPI: %s", e)
            return None

        rates = []
        for pair in PAIRS:
            key = pair.replace("-", "")
            if key not in data:
                logger.warning("Pair %s not found in response", pair)
                continue
            raw = data[key]
            rates.append(
                {
                    "pair": pair,
                    "bid": float(raw["bid"]),
                    "ask": float(raw["ask"]),
                    "high": float(raw["high"]),
                    "low": float(raw["low"]),
                    "change_pct": float(raw["pctChange"]),
                }
            )
            logger.info("%s: bid=%s ask=%s (%s%%)", pair, raw["bid"], raw["ask"], raw["pctChange"])

        return rates or None

    def should_notify(self, pair: str, bid: float, historical_avg: float | None) -> tuple[bool, str]:
        threshold = self._threshold[pair]
        if bid >= threshold:
            return True, f"above fixed threshold (R$ {threshold:.2f})"
        if historical_avg is not None:
            limit = historical_avg * (1 + self._average_percent_above / 100)
            if bid >= limit:
                return True, (
                    f"{self._average_percent_above}% above {self._average_days}-day average "
                    f"(avg: R$ {historical_avg:.4f})"
                )
        return False, ""
