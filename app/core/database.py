import logging

import motor.motor_asyncio
from beanie import init_beanie

from core.config import Settings
from core.models import ExchangeRate

logger = logging.getLogger(__name__)


async def init_db(settings: Settings) -> None:
    client = motor.motor_asyncio.AsyncIOMotorClient(settings.mongo_uri)
    await init_beanie(
        database=client[settings.mongo_db], document_models=[ExchangeRate]
    )
    logger.info("Connected to MongoDB: %s", settings.mongo_db)
