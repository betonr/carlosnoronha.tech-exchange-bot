import pytest

from core.config import Settings


@pytest.fixture
def settings():
    return Settings(
        _env_file=None,
        mongo_uri="mongodb://localhost:27017",
        smtp_host="smtp.example.com",
        smtp_user="bot@example.com",
        smtp_password="secret",
        email_from="bot@example.com",
        email_to="recipient@example.com",
    )


@pytest.fixture
def usd_rate_data():
    return {
        "pair": "USD-BRL",
        "bid": 5.50,
        "ask": 5.55,
        "high": 5.60,
        "low": 5.45,
        "change_pct": 0.5,
    }
