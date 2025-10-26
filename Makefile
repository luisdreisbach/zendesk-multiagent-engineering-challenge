.PHONY: help up upb upd down lint typecheck pre-commit

help:
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z0-9_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Run project
start_dev:
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000


##@ Run project with docker
up: down  ## Start docker compose
	docker compose up

upb: down  ## Start docker compose (with rebuild)
	docker compose up --build

upd: down  ## Start docker compose in detached mode
	docker compose up -d

down: ## Tear down docker compose
	docker compose down

##@ Run static code checks
check: lint typecheck  ## Run all static code checks

lint:  ## Run code linting
	uv run ruff check --no-fix
	uv run ruff format --check

format:  ## Run code formatting (this will modify files!)
	uv run ruff check --fix
	uv run ruff format

typecheck:  ## Run static type checking
	uv run mypy .
