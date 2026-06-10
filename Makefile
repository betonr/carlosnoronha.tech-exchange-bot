.PHONY: help sync lint lint-fix test run up down logs

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

sync: ## Install dependencies (including dev)
	uv sync --dev

lint: ## Run ruff linter
	uv run ruff check app/

lint-fix: ## Run ruff linter and apply auto-fixes
	uv run ruff check app/ --fix

test: ## Run unit tests
	uv run pytest

run: ## Run the bot locally
	uv run python app/main.py

up: ## Start production containers (detached)
	docker compose up -d --build

down: ## Stop production containers
	docker compose down

logs: ## Tail container logs
	docker compose logs -f currency-worker
