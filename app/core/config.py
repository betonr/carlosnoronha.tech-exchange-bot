from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # AwesomeAPI
    awesomeapi_key: str = ""

    # MongoDB
    mongo_uri: str
    mongo_db: str = "currency_worker"

    # SMTP
    smtp_host: str
    smtp_port: int = 587
    smtp_user: str
    smtp_password: str
    email_from: str
    email_to: str

    # Fixed thresholds (BRL)
    threshold_usd: float = 6.20
    threshold_eur: float = 6.80

    # Historical analysis
    average_days: int = 30
    average_percent_above: float = 2.0

    # Operating window (hour range, inclusive start)
    window_start: int = 8
    window_end: int = 20
