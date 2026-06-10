from datetime import datetime, timezone

from beanie import Document
from pydantic import Field
from pymongo import ASCENDING, IndexModel


class ExchangeRate(Document):
    pair: str
    bid: float
    ask: float
    high: float
    low: float
    change_pct: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    notified: bool = False

    class Settings:
        name = "exchange_rates"
        indexes = [
            IndexModel([("pair", ASCENDING), ("timestamp", ASCENDING)]),
            IndexModel([("pair", ASCENDING), ("notified", ASCENDING)]),
        ]
