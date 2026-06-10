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
├── tests/                               # Unit tests (mirrors app/ structure)
│   ├── conftest.py
│   ├── core/
│   │   ├── test_config.py
│   │   ├── test_database.py
│   │   └── test_models.py
│   └── worker/
│       ├── test_scheduler.py
│       ├── repositories/
│       │   └── test_exchange_rate_repository.py
│       └── services/
│           ├── test_email_service.py
│           └── test_exchange_api_service.py
├── .devcontainer/
│   ├── devcontainer.json
│   ├── docker-compose.yml
│   └── Dockerfile
├── .vscode/
│   └── launch.json                      # Debug config for VS Code
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── Makefile
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

To install dev dependencies (linter + tests) inside the container:

```bash
uv sync --dev
# or
make sync
```

### 3. Production

```bash
# Build and start
docker compose up -d --build

# Follow logs
docker compose logs -f currency-worker
```

The production image uses `uv sync --frozen`, so `uv.lock` must be committed to the repository.

## Common commands

All commands are available via `make help`.

| Command | Description |
|---|---|
| `make sync` | Install dependencies including dev |
| `make lint` | Run ruff linter |
| `make lint-fix` | Run ruff and apply auto-fixes |
| `make test` | Run unit tests |
| `make run` | Run the bot locally |
| `make up` | Start production containers (detached) |
| `make down` | Stop production containers |
| `make logs` | Tail container logs |

## Debugging

A VS Code debug configuration is included. Open the **Run and Debug** panel and launch **Exchange Bot** (or press `F5`). The configuration loads `.env` automatically and sets the working directory to `app/`.

## Testing

Unit tests live in `tests/`, mirroring the structure of `app/`. All external dependencies (MongoDB, SMTP, HTTP) are mocked — no real services are needed to run the suite.

```bash
make test
# or
uv run pytest
```

## Linting

[Ruff](https://docs.astral.sh/ruff/) is configured in `pyproject.toml` with the following rule sets: `E`/`W` (pycodestyle), `F` (pyflakes), `I` (isort), `G` (logging format), `UP` (pyupgrade).

```bash
make lint        # check only
make lint-fix    # check and auto-fix
```

## CI/CD

### CI — Tests & Code Quality (`.github/workflows/ci.yml`)

Runs on every push and pull request to `main`, in three parallel jobs:

| Job | What it does |
|---|---|
| `tests` | `pytest` with coverage (`--cov=app`) |
| `lint` | `ruff check` + `ruff format --check` + `mypy` |
| `security` | `bandit` (SAST) + `safety` (dependency vulnerabilities) |

### CD — Build & Deploy (`.github/workflows/cd.yml`)

Runs on push to `main` (ignores `*.md` and `terraform/**` changes), in two sequential jobs:

1. **docker** — builds the image and pushes to Docker Hub (`betonoronha/homol:carlosnoronha.tech-exchange-bot-latest`)
2. **deploy** — SSHes into the VPS, pulls the new image and restarts the containers with `docker compose up -d`

Required GitHub Secrets:

| Secret | Description |
|---|---|
| `DOCKERHUB_USERNAME` | Docker Hub username |
| `DOCKERHUB_TOKEN` | Docker Hub access token |
| `VPS_HOST` | VPS IP or hostname |
| `VPS_USER` | SSH user |
| `VPS_SSH_PRIVATE_KEY` | SSH private key |
| `VPS_PORT` | SSH port (default: `22`) |
| `VPS_COMPOSE_PATH` | Path to `docker-compose.yml` on the VPS |

## Notification logic

An alert is triggered when **any** condition is true:

1. **Fixed threshold** — `bid >= THRESHOLD_USD` (or EUR)
2. **Historical average** — `bid >= 30-day average × (1 + AVERAGE_PERCENT_ABOVE / 100)`

At most **one email per currency per day** is sent.

## Exchange rate API

Uses [AwesomeAPI](https://economia.awesomeapi.com.br) — free, no mandatory authentication. Registering a free API key removes the 1-minute cache and delivers real-time data.

Estimated usage running every 5 minutes between 8h–20h: ~1,440 req/month — well within the free tier of 100k/month.
