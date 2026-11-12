# Обёртка команд для docker compose / uv / npm.
# Рецепты без shell-специфики, чтобы работали и в cmd (make на Windows), и в sh.

COMPOSE := docker compose
COMPOSE_CADDY := $(COMPOSE) -f docker-compose.yml -f docker-compose.caddy.yml
PYTHON_APPS := $(patsubst %/pyproject.toml,%,$(wildcard backend/pyproject.toml bot/pyproject.toml))
HAS_FRONTEND := $(wildcard frontend/package.json)
APP_SERVICES := $(strip $(PYTHON_APPS) $(if $(HAS_FRONTEND),frontend))
SCALE := $(foreach s,$(APP_SERVICES),--scale $(s)=2)

.PHONY: env-check up up-caddy down logs ps migrate webhook lint typecheck test check smoke

env-check:
	$(if $(wildcard .env),,$(error Нет файла .env: скопируйте .env.example в .env и заполните))
	@echo .env found

up: env-check
	$(COMPOSE) up -d --build $(SCALE)

# Production HTTPS: Caddy перед nginx. В .env нужны SITE_ADDRESS и NGINX_PORT_MAPPING.
up-caddy: env-check
	$(COMPOSE_CADDY) up -d --build $(SCALE)

down:
	$(COMPOSE_CADDY) down

logs:
	$(COMPOSE_CADDY) logs -f --tail=200

ps:
	$(COMPOSE_CADDY) ps -a

migrate: env-check
	$(COMPOSE) run --rm migrate

webhook: env-check
	$(COMPOSE) run --rm bot uv run --no-dev --frozen python -m app.set_webhook

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
