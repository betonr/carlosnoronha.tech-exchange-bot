from core.config import Settings


def test_default_values(settings):
    assert settings.threshold_usd == 6.20
    assert settings.threshold_eur == 6.80
    assert settings.average_days == 30
    assert settings.average_percent_above == 2.0
    assert settings.window_start == 8
    assert settings.window_end == 20
    assert settings.mongo_db == "currency_worker"
    assert settings.smtp_port == 587
    assert settings.awesomeapi_key == ""


def test_custom_thresholds():
    s = Settings(
        mongo_uri="mongodb://localhost:27017",
        smtp_host="smtp.example.com",
        smtp_user="u",
        smtp_password="p",
        email_from="a@b.com",
        email_to="c@d.com",
        threshold_usd=7.00,
        threshold_eur=7.50,
    )
    assert s.threshold_usd == 7.00
    assert s.threshold_eur == 7.50


def test_custom_window_and_history():
    s = Settings(
        mongo_uri="mongodb://localhost:27017",
        smtp_host="smtp.example.com",
        smtp_user="u",
        smtp_password="p",
        email_from="a@b.com",
        email_to="c@d.com",
        window_start=9,
        window_end=18,
        average_days=15,
        average_percent_above=3.0,
    )
    assert s.window_start == 9
    assert s.window_end == 18
    assert s.average_days == 15
    assert s.average_percent_above == 3.0
