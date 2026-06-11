from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.database import init_db


@pytest.mark.asyncio
async def test_init_db_connects_with_correct_uri(settings):
    with (
        patch("core.database.motor.motor_asyncio.AsyncIOMotorClient") as mock_client,
        patch("core.database.init_beanie", new_callable=AsyncMock),
    ):
        mock_client.return_value.__getitem__.return_value = MagicMock()
        await init_db(settings)
        mock_client.assert_called_once_with(settings.mongo_uri)


@pytest.mark.asyncio
async def test_init_db_selects_correct_database(settings):
    with (
        patch("core.database.motor.motor_asyncio.AsyncIOMotorClient") as mock_client,
        patch("core.database.init_beanie", new_callable=AsyncMock),
    ):
        mock_client.return_value.__getitem__.return_value = MagicMock()
        await init_db(settings)
        mock_client.return_value.__getitem__.assert_called_once_with(settings.mongo_db)


@pytest.mark.asyncio
async def test_init_db_calls_init_beanie(settings):
    with (
        patch("core.database.motor.motor_asyncio.AsyncIOMotorClient") as mock_client,
        patch("core.database.init_beanie", new_callable=AsyncMock) as mock_init_beanie,
    ):
        mock_db = MagicMock()
        mock_client.return_value.__getitem__.return_value = mock_db
        await init_db(settings)
        mock_init_beanie.assert_called_once()
        _, kwargs = mock_init_beanie.call_args
        assert kwargs["database"] is mock_db
