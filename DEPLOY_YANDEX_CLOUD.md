# Деплой shop_mvp в Яндекс Облако

Пошаговый план для VM + Docker Compose + Caddy (HTTPS) и описание секретов /
переменных окружения.

Локально по-прежнему: `make up` (HTTP :80).  
В облаке: `make up-caddy` + `make webhook`.

---

## 1. Что получается на выходе

Один публичный HTTPS-хост, например `https://shop.example.com`:

| URL | Назначение |
|---|---|
| `/` | каталог (Next.js / Mini App) |
| `/api/products` | публичный API |
| `/health` | health backend |
| `/bot/health` | health bot |
| `/bot/webhook` | Telegram webhook |
| `/media/...` | картинки из MinIO |

`POST /internal/products` снаружи недоступен — только bot → backend внутри Docker-сети.

```
Internet :80/:443
  → Caddy (Let's Encrypt)
    → nginx
      → frontend :3000
      → backend :8000
      → bot :8080
      → minio (/media/)
```

---

## 2. Что подготовить до создания VM

- аккаунт Яндекс Облака и активный платёжный аккаунт;
- домен или поддомен (`shop.example.com`);
- бот в BotFather → `BOT_TOKEN`;
- ваш Telegram user id → `ADMIN_IDS` (узнать: `@userinfobot` или аналог);
- доступ к репозиторию `Gryzly73/shop_mvp` (SSH deploy key или ключ на VM).

Рекомендуемая VM: Ubuntu 22.04/24.04, **2–4 vCPU**, **4–8 GB RAM**, **40–60 GB SSD**, публичный IPv4.

---

## 3. Секреты и переменные

Все значения задаются в файле **`.env` на сервере** (не в git).  
Скопируйте шаблон: `cp .env.example .env && chmod 600 .env`.

### 3.1. Секреты (хранить как тайну)

| Переменная | Кто использует | Как получить / сгенерировать | Правила |
|---|---|---|---|
| `BOT_TOKEN` | bot | BotFather → бот → API Token | В production нельзя оставлять `123456:replace-...` |
| `WEBHOOK_SECRET` | bot ↔ Telegram | `openssl rand -hex 24` | Только символы `A-Z a-z 0-9 _ -` (заголовок Telegram Secret Token) |
| `SERVICE_TOKEN` | bot + backend | `openssl rand -hex 24` | Один и тот же токен в обоих сервисах; заголовок `X-Service-Token` |
| `POSTGRES_PASSWORD` | postgres, migrate, backend | `openssl rand -hex 24` | Не `change-me*` |
| `MINIO_ROOT_USER` | minio, minio-init, backend | придумать логин, напр. `shopmedia` | В production **нельзя** `minioadmin` |
| `MINIO_ROOT_PASSWORD` | minio, minio-init, backend | `openssl rand -hex 24` | **Без** символов `@ : /` (подставляется в URL для `mc`) |

### 3.2. Конфигурация (не секрет, но обязательна)

| Переменная | Пример для облака | Зачем |
|---|---|---|
| `APP_ENV` | `production` | Включает строгие проверки секретов и HTTPS |
| `POSTGRES_DB` | `shop` | Имя БД |
| `POSTGRES_USER` | `shop` | Пользователь БД |
| `POSTGRES_HOST` | `postgres` | Имя сервиса в Compose (на VM не менять) |
| `POSTGRES_PORT` | `5432` | Порт Postgres |
| `S3_ENDPOINT` | `http://minio:9000` | Внутренний адрес MinIO |
| `S3_BUCKET` | `products` | Бакет картинок |
| `PUBLIC_BASE_URL` | `https://shop.example.com` | Mini App + база для webhook; **только https://** |
| `PUBLIC_MEDIA_URL` | `https://shop.example.com/media/` | URL картинок в API; **только https://**, со `/` в конце |
| `ADMIN_IDS` | `1234567890` | Telegram id админов через запятую; не оставлять пример `123456789` |
| `BACKEND_INTERNAL_URL` | `http://backend:8000` | SSR frontend и bot → API |
| `SITE_ADDRESS` | `shop.example.com` | Хост для Caddy **без** `https://` |
| `NGINX_PORT_MAPPING` | `127.0.0.1:8080:80` | Чтобы :80/:443 занял Caddy |

### 3.3. Кто какие переменные видит

Compose передаёт сервисам только нужное (не весь `.env` целиком):

| Сервис | Переменные |
|---|---|
| postgres | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` |
| minio | `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD` |
| minio-init | `MINIO_ROOT_*`, `S3_BUCKET` |
| migrate | `POSTGRES_*` (+ опционально `DATABASE_URL`) |
| backend | `APP_ENV`, `POSTGRES_*`, `MINIO_ROOT_*`, `S3_*`, `PUBLIC_MEDIA_URL`, `SERVICE_TOKEN` |
| bot | `APP_ENV`, `BOT_TOKEN`, `WEBHOOK_SECRET`, `ADMIN_IDS`, `PUBLIC_BASE_URL`, `SERVICE_TOKEN`, `BACKEND_INTERNAL_URL` |
| frontend | `BACKEND_INTERNAL_URL` |
| caddy | `SITE_ADDRESS` |
| nginx | `NGINX_PORT_MAPPING` (публикация порта на хосте) |

### 3.4. Готовый шаблон `.env` для Яндекс Облака

Подставьте свои значения вместо `<...>`.

```env
APP_ENV=production

POSTGRES_DB=shop
POSTGRES_USER=shop
POSTGRES_PASSWORD=<openssl rand -hex 24>
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

MINIO_ROOT_USER=shopmedia
MINIO_ROOT_PASSWORD=<openssl rand -hex 24>
S3_ENDPOINT=http://minio:9000
S3_BUCKET=products

PUBLIC_BASE_URL=https://shop.example.com
PUBLIC_MEDIA_URL=https://shop.example.com/media/

BOT_TOKEN=<токен_от_BotFather>
WEBHOOK_SECRET=<openssl rand -hex 24>
ADMIN_IDS=<ваш_telegram_id>
SERVICE_TOKEN=<openssl rand -hex 24>
BACKEND_INTERNAL_URL=http://backend:8000

SITE_ADDRESS=shop.example.com
NGINX_PORT_MAPPING=127.0.0.1:8080:80
```

Генерация на сервере:

```bash
openssl rand -hex 24
```

### 3.5. Секреты вне `.env` (инфраструктура)

| Секрет / ключ | Где хранится | Зачем |
|---|---|---|
| SSH-ключ доступа к VM | ваш ПК + метаданные VM в YC | вход по SSH |
| Deploy key / SSH key для GitHub | `~/.ssh` на VM | `git clone` / `git pull` private-репо |
| DNS у регистратора | панель DNS | A-запись на IP VM |
| (опционально) ключи Object Storage | позже, при замене MinIO | S3 API Яндекса |

**Не коммитьте** `.env`, ключи SSH, дампы БД с продом.

---

## 4. Пошаговый деплой

### Шаг 1. Сеть и VM в Яндекс Облаке

1. Создайте VPC и подсеть (если нет).
2. Security Group:
   - inbound **22/tcp** — желательно только ваш IP;
   - inbound **80/tcp**, **443/tcp** — `0.0.0.0/0`;
   - outbound — all.
3. Создайте VM (Ubuntu), публичный IPv4, SSH-ключ, эта SG.
4. Запишите публичный IP.

Не открывайте наружу **5432** и **9001**.

### Шаг 2. DNS

```text
A  shop.example.com  →  <публичный IP VM>
```

Дождитесь резолва **до** `make up-caddy`, иначе Let's Encrypt не выдаст сертификат.

### Шаг 3. ПО на VM

```bash
ssh ubuntu@<IP>

sudo apt update
sudo apt install -y git make ca-certificates curl
# Docker Engine + Compose plugin — по официальной инструкции Docker
sudo usermod -aG docker $USER
# перелогиньтесь в SSH

docker version
docker compose version
```

### Шаг 4. Код

```bash
sudo mkdir -p /opt/shop_mvp
sudo chown "$USER:$USER" /opt/shop_mvp
git clone git@github.com:Gryzly73/shop_mvp.git /opt/shop_mvp
cd /opt/shop_mvp
```

### Шаг 5. Заполнить секреты

```bash
cp .env.example .env
chmod 600 .env
nano .env
```

Заполните по разделу 3. Сохраните резервную копию `.env` в менеджере паролей / Lockbox, не в git.

### Шаг 6. Поднять стек с HTTPS

```bash
make up-caddy
```

Эквивалент:

```bash
docker compose -f docker-compose.yml -f docker-compose.caddy.yml \
  up -d --build --scale backend=2 --scale bot=2 --scale frontend=2
```

Проверки:

```bash
curl -sS https://shop.example.com/health
curl -sS https://shop.example.com/bot/health
curl -sS https://shop.example.com/api/products
curl -sS -o /dev/null -w "%{http_code}\n" https://shop.example.com/
```

Если нет сертификата: DNS, SG 80/443, логи `caddy`.

### Шаг 7. Зарегистрировать Telegram webhook

```bash
make webhook
```

Проверка:

```bash
curl -sS "https://api.telegram.org/bot<BOT_TOKEN>/getWebhookInfo"
```

Ожидается `https://shop.example.com/bot/webhook` без ошибок SSL.

### Шаг 8. Приёмка

1. Каталог открывается по HTTPS.
2. В боте `/start` → «Открыть каталог».
3. Админ: фото с подписью → «Товар создан».
4. Картинка по `/media/...` открывается.
5. Повтор того же фото → «Такой товар уже есть».
6. `https://shop.example.com/internal/products` снаружи → 404/405.

---

## 5. Обновление и сопровождение

```bash
cd /opt/shop_mvp
git pull
make up-caddy
make migrate    # если менялась схема БД
make webhook    # если менялись PUBLIC_BASE_URL / BOT_TOKEN / WEBHOOK_SECRET
```

Логи: `make logs` или  
`docker compose -f docker-compose.yml -f docker-compose.caddy.yml logs -f caddy bot backend`.

### Бэкапы

- ежедневно `pg_dump` Postgres;
- том/данные MinIO (картинки не в БД);
- копия `.env` в безопасном хранилище.

```bash
docker compose exec -T postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" \
  > "shop-$(date +%F).sql"
```

Снимок диска VM — дополнение, не замена дампа.

### Ротация секретов

| Секрет | Как ротировать |
|---|---|
| `SERVICE_TOKEN` | новый токен в `.env` → `make up-caddy` (bot + backend вместе) |
| `WEBHOOK_SECRET` | новый в `.env` → `make up-caddy` → `make webhook` |
| `BOT_TOKEN` | новый от BotFather → `.env` → `make up-caddy` → `make webhook` |
| `POSTGRES_PASSWORD` | сменить в Postgres и `.env`, пересоздать связанные сервисы |
| `MINIO_ROOT_*` | сменить в MinIO и `.env`; при потере ключа доступ к бакету ломается |

---

## 6. Типичные ошибки

| Симптом | Частая причина |
|---|---|
| Сервис не стартует в `production` | остался `change-me*`, `minioadmin`, HTTP в `PUBLIC_*`, примерный `ADMIN_IDS` |
| Caddy без сертификата | DNS ещё не указывает на IP, закрыт 80 порт |
| Mini App без картинок | `PUBLIC_MEDIA_URL` не https или неверный хост |
| Webhook не доходит | не выполнен `make webhook`, неверный `WEBHOOK_SECRET` |
| Bot «Не удалось создать товар» | разный `SERVICE_TOKEN` у bot и backend |
| 502 на сайте | ещё не healthy backend/frontend; `make ps` / логи |

---

## 7. Дальше (не обязательно в первый день)

1. Managed PostgreSQL → поменять `POSTGRES_HOST` / пароль.
2. Object Storage вместо MinIO → `S3_ENDPOINT` и ключи доступа.
3. Uptime на `https://shop.example.com/health`.
4. Секреты в Yandex Lockbox + выдача на VM при деплое.

Kubernetes / ALB для текущего MVP не нужны.
