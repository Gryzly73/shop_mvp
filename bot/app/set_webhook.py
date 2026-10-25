import asyncio

from aiogram import Bot
from aiogram.types import MenuButtonWebApp, WebAppInfo

from app.keyboards import webapp_url
from app.settings import Settings, load_settings


def build_webhook_url(public_base_url: str) -> str:
    return webapp_url(public_base_url) + "/bot/webhook"


async def setup_webhook(bot: Bot, settings: Settings) -> None:
    """Регистрирует webhook и кнопку меню. Отдельная команда, чтобы реплики не спорили."""
    await bot.set_webhook(
        url=build_webhook_url(settings.public_base_url),
        secret_token=settings.webhook_secret,
    )
    await bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(
            text="Каталог",
            web_app=WebAppInfo(url=webapp_url(settings.public_base_url)),
        )
    )


async def _main() -> None:
    settings = load_settings()
    bot = Bot(token=settings.bot_token)
    try:
        await setup_webhook(bot, settings)
    finally:
        await bot.session.close()


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
