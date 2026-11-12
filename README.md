# shop_mvp

MVP каталога товаров: администратор добавляет товар через Telegram-бота, изображение
сохраняется в MinIO, данные — в PostgreSQL, каталог отображается приложением Next.js
в браузере и Telegram Mini App.

## Стек

- Next.js App Router;
- FastAPI, SQLAlchemy и Alembic;
- aiogram 3 в webhook-режиме;
- PostgreSQL и MinIO;
- nginx и Docker Compose.

## Настройка

1. Скопируйте `.env.example` в `.env`.
2. Укажите настоящий `BOT_TOKEN`, Telegram ID администраторов и случайные значения
   `POSTGRES_PASSWORD`, `MINIO_ROOT_PASSWORD`, `WEBHOOK_SECRET`, `SERVICE_TOKEN`.
3. Для публичного запуска задайте:

   ```env
   APP_ENV=production
   PUBLIC_BASE_URL=https://shop.example.com
   PUBLIC_MEDIA_URL=https://shop.example.com/media/
   ```

   В production приложение отклоняет шаблонные секреты, `minioadmin`, примерный
   `ADMIN_IDS` и HTTP-адреса Mini App / media.

Для локальной разработки оставьте `APP_ENV=development` и
`PUBLIC_BASE_URL=http://localhost`.

## Запуск

```sh
make up
```

Команда собирает и поднимает по две реплики backend, bot и frontend. Без `make`:

```sh
docker compose up -d --build --scale backend=2 --scale bot=2 --scale frontend=2
```

### Production HTTPS (VPS / Яндекс Облако)

Caddy получает сертификат Let's Encrypt и проксирует на nginx. В `.env`:

```env
APP_ENV=production
PUBLIC_BASE_URL=https://shop.example.com
PUBLIC_MEDIA_URL=https://shop.example.com/media/
SITE_ADDRESS=shop.example.com
NGINX_PORT_MAPPING=127.0.0.1:8080:80
```

```sh
make up-caddy
make webhook
```

Пошаговый план и список секретов: [DEPLOY_YANDEX_CLOUD.md](DEPLOY_YANDEX_CLOUD.md).

После запуска:

- каталог: `http://localhost/`;
- API каталога: `http://localhost/api/products`;
- health backend: `http://localhost/health`;
- health bot: `http://localhost/bot/health`;
- консоль MinIO: `http://localhost:9001`.

`POST /internal/products` намеренно не публикуется через nginx. К нему обращается только
бот внутри Docker-сети.

## Telegram Mini App

Telegram требует публичный HTTPS URL. Для временной локальной проверки можно запустить
туннель:

```sh
cloudflared tunnel --url http://localhost:80
```

Запишите полученный HTTPS URL в `PUBLIC_BASE_URL`, а `<URL>/media/` — в
`PUBLIC_MEDIA_URL`, пересоздайте сервисы и зарегистрируйте webhook:

```sh
docker compose run --rm bot uv run --no-dev --frozen python -m app.set_webhook
```

Команда также устанавливает кнопку меню «Каталог». Ручная проверка описана в
`docs/TELEGRAM_CHECKLIST.md`.

## Проверки

Полная статическая и тестовая проверка:

```sh
make check
```

Проверка stateless и отказа реплик:

```sh
make smoke
```

Smoke-тест:

1. поднимает по две реплики приложений;
2. подтверждает балансировку через заголовок `X-Instance`;
3. проверяет идемпотентное создание товара;
4. останавливает по одной реплике backend, bot и frontend;
5. повторяет запросы на оставшихся репликах;
6. перезапускает PostgreSQL, MinIO и приложения и проверяет сохранность товара.

Smoke-тест создаёт товар с названием `stateless-smoke-<случайный id>`.

## Почему сервисы stateless

- backend хранит данные только в PostgreSQL и MinIO; сессия БД создаётся на запрос;
- bot не использует polling, FSM и локальное хранилище состояния;
- повтор webhook безопасен благодаря уникальному `photo_file_unique_id`;
- frontend отключает серверное кэширование каталога;
- файлы обрабатываются в памяти и не записываются на локальный диск;
- миграции выполняются отдельным одноразовым сервисом;
- клиенты и пулы создаются на жизненный цикл процесса, а не разделяются между репликами.

Остановить стенд:

```sh
make down
```
