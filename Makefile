# Тонкие обёртки над docker compose / uv / npm.
# Рецепты без shell-конструкций, чтобы работать и в cmd (make на Windows), и в sh.
# Цели для ещё не созданных частей (backend, bot, frontend) пропускаются.

COMPOSE := docker compose
PYTHON_APPS := $(patsubst %/pyproject.toml,%,$(wildcard backend/pyproject.toml bot/pyproject.toml))
HAS_FRONTEND := $(wildcard frontend/package.json)
APP_SERVICES := $(strip $(PYTHON_APPS) $(if $(HAS_FRONTEND),frontend))
SCALE := $(foreach s,$(APP_SERVICES),--scale $(s)=2)

.PHONY: env-check up down logs ps migrate lint typecheck test check smoke

env-check:
	$(if $(wildcard .env),,$(error Нет файла .env: скопируйте .env.example в .env и заполните))
	@echo .env found

up: env-check
	$(COMPOSE) up -d --build $(SCALE)

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f --tail=200

ps:
	$(COMPOSE) ps -a

migrate: env-check
	$(COMPOSE) run --rm migrate

lint:
	@echo lint: $(or $(APP_SERVICES),nothing to lint yet)
	$(foreach app,$(PYTHON_APPS),cd $(app) && uv run ruff check . && uv run ruff format --check .$(newline))
	$(if $(HAS_FRONTEND),cd frontend && npm run lint)

typecheck:
	@echo typecheck: $(or $(APP_SERVICES),nothing to typecheck yet)
	$(foreach app,$(PYTHON_APPS),cd $(app) && uv run mypy app$(newline))
	$(if $(HAS_FRONTEND),cd frontend && npx tsc --noEmit)

test:
	@echo test: $(or $(PYTHON_APPS),nothing to test yet)
	$(foreach app,$(PYTHON_APPS),cd $(app) && uv run pytest$(newline))

check: lint typecheck test
	@echo check: OK

smoke: env-check
	uv run --with httpx python scripts/check_stateless.py

define newline


endef
