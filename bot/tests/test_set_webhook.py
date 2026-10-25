from aiogram import Bot
from aiogram.methods import SetChatMenuButton, SetWebhook
from aiogram.types import MenuButtonWebApp

from app.set_webhook import build_webhook_url, setup_webhook
from app.settings import Settings
from tests.fakes import FakeSession


def _settings(public_base_url: str) -> Settings:
    return Settings(
        bot_token="123456:test-token",
        webhook_secret="wh-secret",
        admin_ids="10",
        public_base_url=public_base_url,
        service_token="svc",
        backend_internal_url="http://backend:8000",
    )


def test_webhook_url_joins_the_public_origin() -> None:
    assert build_webhook_url("https://shop.example") == "https://shop.example/bot/webhook"
    assert build_webhook_url("https://shop.example/") == "https://shop.example/bot/webhook"


async def test_setup_webhook_registers_url_secret_and_menu_button() -> None:
    session = FakeSession()
    bot = Bot(token="123456:test-token", session=session)
    try:
        await setup_webhook(bot, _settings("https://shop.example/"))
    finally:
        await session.close()

    assert isinstance(session.calls[0], SetWebhook)
    assert session.calls[0].url == "https://shop.example/bot/webhook"
    assert session.calls[0].secret_token == "wh-secret"
    assert isinstance(session.calls[1], SetChatMenuButton)
    button = session.calls[1].menu_button
    assert isinstance(button, MenuButtonWebApp)
    assert button.web_app.url == "https://shop.example"
    assert button.text == "Каталог"
