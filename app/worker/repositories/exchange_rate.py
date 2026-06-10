import logging
from datetime import datetime, timedelta, timezone

from core.models import ExchangeRate

logger = logging.getLogger(__name__)


class ExchangeRateRepository:
    async def save(self, rate_data: dict) -> ExchangeRate:
        rate = ExchangeRate(**rate_data)
        await rate.insert()
        logger.debug(f"Saved rate: {rate.id}")
        return rate

    async def get_historical_average(self, pair: str, days: int) -> float | None:
        since = datetime.now(tz=timezone.utc) - timedelta(days=days)
        pipeline = [
            {"$match": {"pair": pair, "timestamp": {"$gte": since}}},
            {"$group": {"_id": None, "average": {"$avg": "$bid"}, "count": {"$sum": 1}}},
        ]
        result = await ExchangeRate.aggregate(pipeline).to_list()
        if not result or result[0]["count"] < 10:
            count = result[0]["count"] if result else 0
            logger.info(f"Insufficient samples for {pair} historical average ({count} records)")
            return None
        avg = result[0]["average"]
        logger.info(f"{days}-day average for {pair}: R$ {avg:.4f} ({result[0]['count']} samples)")
        return avg

    async def already_notified_today(self, pair: str) -> bool:
        start_of_day = datetime.now(tz=timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        found = await ExchangeRate.find_one(
            ExchangeRate.pair == pair,
            ExchangeRate.notified == True,
            ExchangeRate.timestamp >= start_of_day,
        )
        return found is not None

    async def mark_as_notified(self, rate: ExchangeRate) -> None:
        rate.notified = True
        await rate.save()
