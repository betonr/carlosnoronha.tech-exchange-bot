# Exchange Bot

Python worker that monitors USD and EUR exchange rates against BRL and sends email alerts when rates hit configured thresholds.

## Stack

- **Python 3.12**
- **Beanie** (ODM) + **Motor** (async MongoDB driver) — MongoDB Atlas
- **pydantic-settings** — environment config
- **requests** — HTTP calls to AwesomeAPI
- **uv** — package manager
- **ruff** — linter and formatter (dev dependency)
- **pytest** + **pytest-asyncio** — test suite (dev dependency)
- **Docker** + **devcontainer** — local dev and production deployment
- **GitHub Actions** — CI (tests + lint + security) and CD (Docker build + VPS deploy)

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
tests/                               # Unit tests — mirrors app/ structure
├── conftest.py                      # Shared fixtures (settings, usd_rate_data)
├── core/
│   ├── test_config.py
│   ├── test_database.py
│   └── test_models.py
└── worker/
    ├── test_scheduler.py
    ├── repositories/
    │   └── test_exchange_rate_repository.py
    └── services/
        ├── test_email_service.py
        └── test_exchange_api_service.py
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

## Common commands (Makefile)

```bash
make sync        # uv sync --dev
make lint        # ruff check app/
make lint-fix    # ruff check app/ --fix
make test        # uv run pytest
make run         # uv run python app/main.py
make up          # docker compose up -d --build
make down        # docker compose down
make logs        # docker compose logs -f currency-worker
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

## CI/CD

### CI (`.github/workflows/ci.yml`)

Runs on push and PR to `main` — three parallel jobs: `tests` (pytest + coverage), `lint` (ruff + mypy), `security` (bandit + safety).

### CD (`.github/workflows/cd.yml`)

Runs on push to `main` (ignores `*.md` and `terraform/**`):
1. Builds and pushes Docker image to Docker Hub
2. SSHes into VPS and runs `docker compose pull && docker compose up -d`

Required GitHub Secrets: `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`, `VPS_HOST`, `VPS_USER`, `VPS_SSH_PRIVATE_KEY`, `VPS_PORT`, `VPS_COMPOSE_PATH`.

## Testing

All external dependencies (MongoDB, SMTP, HTTP) are mocked — no real services needed. Tests mirror `app/` structure. Run with `make test`.

Key mocking patterns:
- Beanie `Document` instantiation requires `get_pymongo_collection` to be patched (no `init_beanie` in tests)
- `MagicMock.__ge__` returns `NotImplemented` by default — set `.return_value` explicitly when mocking `>=` comparisons with `datetime`
- MIME email body is base64-encoded when content contains non-ASCII (emoji) — use `email.message_from_string` to decode before asserting

## Adding a new model

1. Create the Beanie Document in `core/models.py`
2. Register it in `core/database.py` → `document_models=[..., NewModel]`
3. Create `worker/repositories/new_model.py` with a repository class
