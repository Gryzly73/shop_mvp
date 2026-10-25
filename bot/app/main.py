import httpx
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler
from aiohttp import web

from app.backend_client import BackendClient
from app.handlers import create_router
from app.settings import load_settings

WEBHOOK_PATH = "/bot/webhook"
LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = 8080
_HTTP_CLIENT: web.AppKey[httpx.AsyncClient] = web.AppKey("http_client", httpx.AsyncClient)


async def health(_request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


def create_app() -> web.Application:
    settings = load_settings()
    bot = Bot(token=settings.bot_token)
    # FSM выключен: диалог ничего не запоминает, любая реплика берёт любое обновление.
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(
        create_router(
            admin_ids=settings.admin_id_list(),
            public_base_url=settings.public_base_url,
        )
    )

    application = web.Application()
    SimpleRequestHandler(
        dispatcher=dispatcher,
        bot=bot,
        secret_token=settings.webhook_secret,
        handle_in_background=False,
    ).register(application, path=WEBHOOK_PATH)
    application.router.add_get("/health", health)

    async def on_startup(app: web.Application) -> None:
        http_client = httpx.AsyncClient(timeout=30.0, trust_env=False)
        app[_HTTP_CLIENT] = http_client
        dispatcher["backend_client"] = BackendClient(
            http_client,
            base_url=settings.backend_internal_url,
            service_token=settings.service_token,
        )

    async def on_cleanup(app: web.Application) -> None:
        http_client = app.get(_HTTP_CLIENT)
        if http_client is not None:
            await http_client.aclose()

    application.on_startup.append(on_startup)
    application.on_cleanup.append(on_cleanup)
    return application


def main() -> None:
    web.run_app(create_app(), host=LISTEN_HOST, port=LISTEN_PORT)


if __name__ == "__main__":
    main()
