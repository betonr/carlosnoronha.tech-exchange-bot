import asyncio
import logging
import sys

from core.config import Settings
from core.database import init_db
from worker.scheduler import Scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)


async def main() -> None:
    settings = Settings()
    await init_db(settings)
    await Scheduler(settings).run()


if __name__ == "__main__":
    asyncio.run(main())
