# Exchange Bot

Python worker that monitors USD and EUR exchange rates against BRL and sends email alerts when rates hit configured thresholds.

## Project structure

```
exchange-bot/
├── app/
│   ├── main.py                          # Entry point
│   ├── core/
│   │   ├── config.py                    # Settings via pydantic-settings
│   │   ├── database.py                  # MongoDB connection (Beanie + Motor)
│   │   └── models.py                    # Beanie document models
│   └── worker/
│       ├── scheduler.py                 # Scheduler class — main loop
│       ├── repositories/
│       │   └── exchange_rate.py         # ExchangeRateRepository
│       └── services/
│           ├── exchange_api.py          # ExchangeApiService — fetch & evaluate rates
│           └── email.py                 # EmailService — SMTP alert emails
├── .devcontainer/
│   ├── devcontainer.json
│   ├── docker-compose.yml
│   └── Dockerfile
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
└── pyproject.toml
```

## Getting started

### 1. Configure environment variables

```bash
cp .env.example .env
# fill in your values
```

| Variable | Description |
|---|---|
| `MONGO_URI` | MongoDB Atlas connection string |
| `SMTP_HOST` / `SMTP_PORT` | SMTP server (default port: `587`) |
| `SMTP_USER` / `SMTP_PASSWORD` | SMTP credentials |
| `EMAIL_FROM` / `EMAIL_TO` | Sender and recipient addresses |
| `THRESHOLD_USD` | Fixed BRL threshold for USD alerts (e.g. `6.20`) |
| `THRESHOLD_EUR` | Fixed BRL threshold for EUR alerts (e.g. `6.80`) |
| `AVERAGE_DAYS` | Historical window for average calculation (default: `30`) |
| `AVERAGE_PERCENT_ABOVE` | % above average to trigger alert (default: `2.0`) |
| `WINDOW_START` / `WINDOW_END` | Operating hours, inclusive start (default: `8` and `20`) |
| `AWESOMEAPI_KEY` | AwesomeAPI key (optional, removes 1-min cache) |

### 2. Development (devcontainer)

Open the project in VS Code and select **Reopen in Container**. On first start, `uv sync` installs all dependencies into `.venv` automatically.

Before opening for the first time, generate the lock file locally if you have `uv` installed:

```bash
uv lock
```

### 3. Production

```bash
# Build and start
docker compose up -d --build

# Follow logs
docker compose logs -f currency-worker
```

The production image uses `uv sync --frozen`, so `uv.lock` must be committed to the repository.

## Notification logic

An alert is triggered when **any** condition is true:

1. **Fixed threshold** — `bid >= THRESHOLD_USD` (or EUR)
2. **Historical average** — `bid >= 30-day average × (1 + AVERAGE_PERCENT_ABOVE / 100)`

At most **one email per currency per day** is sent.

## Exchange rate API

Uses [AwesomeAPI](https://economia.awesomeapi.com.br) — free, no mandatory authentication. Registering a free API key removes the 1-minute cache and delivers real-time data.

Estimated usage running every 5 minutes between 8h–20h: ~1,440 req/month — well within the free tier of 100k/month.
