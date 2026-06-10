import asyncio
import logging
from datetime import datetime

from core.config import Settings
from worker.repositories.exchange_rate import ExchangeRateRepository
from worker.services.email import EmailService
from worker.services.exchange_api import ExchangeApiService

logger = logging.getLogger(__name__)

INTERVAL_SECONDS = 300  # 5 minutes


class Scheduler:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._api = ExchangeApiService(settings)
        self._email = EmailService(settings)
        self._repo = ExchangeRateRepository()

    def _within_window(self) -> bool:
        return self._settings.window_start <= datetime.now().hour < self._settings.window_end

    async def _run_cycle(self) -> None:
        if not self._within_window():
            logger.info(f"Outside operating window ({self._settings.window_start}h–{self._settings.window_end}h). Skipping.")
            return

        logger.info("Starting check cycle...")
        rates = self._api.fetch_rates()
        if not rates:
            logger.warning("No rates returned. Aborting cycle.")
            return

        for rate_data in rates:
            pair = rate_data["pair"]
            saved = await self._repo.save(rate_data)

            if await self._repo.already_notified_today(pair):
                logger.info(f"{pair}: already notified today. Skipping.")
                continue

            avg = await self._repo.get_historical_average(pair, self._settings.average_days)
            notify, reason = self._api.should_notify(pair, rate_data["bid"], avg)

            if notify:
                logger.info(f"{pair}: ALERT — {reason}")
                try:
                    self._email.send_alert(rate_data, reason)
                    await self._repo.mark_as_notified(saved)
                except Exception:
                    logger.error(f"{pair}: failed to send email. Will retry next cycle.")
            else:
                logger.info(f"{pair}: R$ {rate_data['bid']:.4f} — no alert.")

        logger.info("Cycle complete.")

    async def run(self) -> None:
        logger.info("Exchange Bot started.")
        logger.info(f"  Thresholds: USD > R$ {self._settings.threshold_usd} | EUR > R$ {self._settings.threshold_eur}")
        logger.info(f"  Historical: {self._settings.average_percent_above}% above {self._settings.average_days}-day average")
        logger.info(f"  Window: {self._settings.window_start}h–{self._settings.window_end}h | Interval: {INTERVAL_SECONDS // 60} min")

        while True:
            await self._run_cycle()
            await asyncio.sleep(INTERVAL_SECONDS)
