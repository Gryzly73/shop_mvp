from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo


def webapp_url(public_base_url: str) -> str:
    return public_base_url.strip().rstrip("/")


def catalog_keyboard(public_base_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Открыть каталог",
                    web_app=WebAppInfo(url=webapp_url(public_base_url)),
                )
            ]
        ]
    )
