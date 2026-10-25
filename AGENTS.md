# AGENTS.md — shop_mvp

MVP интернет-магазина: каталог товаров (Next.js, открывается как Telegram Mini App) и Telegram-бот, через который админ добавляет товары. Полный план — [docs/PLAN.md](docs/PLAN.md).

## Стек

| Часть | Технологии |
|---|---|
| backend | Python 3.12, FastAPI, SQLAlchemy 2 (async, asyncpg), Alembic, aioboto3, pydantic-settings, uv |
| bot | Python 3.12, aiogram 3 (только webhook), httpx, uv |
| frontend | Next.js (App Router), TypeScript, без CSS-фреймворков |
| инфраструктура | PostgreSQL, MinIO (S3), nginx, Docker Compose |

Все сервисы приложения (backend, bot, frontend) работают минимум в 2 репликах за nginx. Любая реплика должна уметь обработать любой запрос.

## Слои backend (чистая архитектура)

```
app/domain/          сущности и порты (Protocol). Не импортирует ничего из app.* и сторонних фреймворков
app/application/     use cases. Зависит только от app.domain
app/infrastructure/  адаптеры: БД, MinIO, настройки. Реализует порты из domain
app/api/             FastAPI-роуты, схемы, DI. Внешний слой
app/main.py          сборка приложения (composition root)
```

Зависимости направлены только внутрь: `api`, `infrastructure` → `application` → `domain`. Use cases получают адаптеры через конструктор, а не импортируют их.

## Запрещено

- polling в боте (`start_polling`, `run_polling`) — только webhook;
- `MemoryStorage` и любое FSM-хранилище в памяти процесса;
- запись на локальный диск: `open(..., 'w')`, `tempfile`, `next/image` с дисковым кэшем, загрузка файлов во временные файлы. Файлы обрабатываются в памяти (`BytesIO`) и уходят в MinIO;
- глобальные изменяемые объекты на уровне модуля (клиенты, сессии, словари, счётчики). Клиенты и пулы создаются в lifespan приложения;
- кэши в памяти процесса (`functools.lru_cache` на данных, словари-кэши, ISR/кэш fetch в Next.js — только `cache: 'no-store'` и `force-dynamic`);
- миграции при старте приложения — только отдельный одноразовый сервис `migrate`;
- установка webhook в `on_startup` бота — только отдельной командой `python -m app.set_webhook`;
- прямой доступ бота к базе или к MinIO — только через `POST /internal/products` backend;
- секреты в коде и в git: всё через переменные окружения (`.env`, шаблон — `.env.example`).

## Идемпотентность

Telegram может повторить webhook. Создание товара идемпотентно по `photo_file_unique_id`: `INSERT ... ON CONFLICT DO NOTHING`, при дубле возвращается существующая запись.

## Команды

```
make up        поднять стенд (реплики x2)
make down      остановить
make logs      логи
make migrate   применить миграции
make check     lint + typecheck + test
make smoke     проверка stateless (scripts/check_stateless.py)
```

На Windows `make` запускается из PowerShell, Git Bash или WSL; если make нет — выполняйте команды из `Makefile` вручную.

## Правило работы

После каждого шага плана запускать `make check` и проверку из раздела «Проверка» этого шага в [docs/PLAN.md](docs/PLAN.md). Шаг не считается выполненным, пока проверка не прошла.
