# Exchange Bot

Python worker that monitors USD and EUR exchange rates against BRL and sends email alerts when rates hit configured thresholds.

## Stack

- **Python 3.12**
- **Beanie** (ODM) + **Motor** (async MongoDB driver) — MongoDB Atlas
- **pydantic-settings** — environment config
- **requests** — HTTP calls to AwesomeAPI
- **uv** — package manager
- **Docker** + **devcontainer** — local dev and production deployment

## Project structure

```
app/
├── main.py                          # Entry point — init DB, start Scheduler
├── core/
│   ├── config.py                    # Settings (pydantic-settings, loads .env)
│   ├── database.py                  # init_db() — connects Motor + Beanie
│   └── models.py                    # ExchangeRate (Beanie Document)
└── worker/
    ├── scheduler.py                 # Scheduler class — async loop, run_cycle
    ├── repositories/
    │   └── exchange_rate.py         # ExchangeRateRepository
    └── services/
        ├── exchange_api.py          # ExchangeApiService — fetch & evaluate rates
        └── email.py                 # EmailService — SMTP alert emails
```

## Architecture

- `main.py` calls `init_db(settings)` then `Scheduler(settings).run()`
- `Scheduler` owns one instance of each collaborator: `ExchangeApiService`, `EmailService`, `ExchangeRateRepository`
- Each cycle: fetch rates → save to DB → check if already notified today → evaluate thresholds → send email if needed
- Async throughout (`asyncio`) — Beanie/Motor for DB, `asyncio.sleep` for scheduling

## Running locally

Requires a `.env` file (copy from `.env.example`). Open in VS Code and **Reopen in Container** — `uv sync` runs automatically on first start.

```bash
uv lock          # generate lock file (first time only)
# then reopen in devcontainer
```

## Running in production

```bash
docker compose up -d --build
docker compose logs -f currency-worker
```

`uv.lock` must be committed — production image uses `uv sync --frozen`.

## Environment variables

| Variable | Description |
|---|---|
| `MONGO_URI` | MongoDB Atlas connection string |
| `SMTP_HOST` / `SMTP_PORT` | SMTP server |
| `SMTP_USER` / `SMTP_PASSWORD` | SMTP credentials |
| `EMAIL_FROM` / `EMAIL_TO` | Sender and recipient |
| `THRESHOLD_USD` | Fixed BRL threshold for USD (default: `6.20`) |
| `THRESHOLD_EUR` | Fixed BRL threshold for EUR (default: `6.80`) |
| `AVERAGE_DAYS` | Historical window in days (default: `30`) |
| `AVERAGE_PERCENT_ABOVE` | % above average to trigger alert (default: `2.0`) |
| `WINDOW_START` / `WINDOW_END` | Operating hours (default: `8` / `20`) |
| `AWESOMEAPI_KEY` | Optional — removes AwesomeAPI 1-min cache |

## Notification logic

Alert fires when **any** condition is true:

1. `bid >= THRESHOLD_USD` (or EUR)
2. `bid >= 30-day average × (1 + AVERAGE_PERCENT_ABOVE / 100)`

At most one email per currency per day.

## Adding a new model

1. Create the Beanie Document in `core/models.py`
2. Register it in `core/database.py` → `document_models=[..., NewModel]`
3. Create `worker/repositories/new_model.py` with a repository class
