from collections.abc import Sequence
from io import BytesIO

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import Message

from app.backend_client import BackendClient, BackendRequestError
from app.keyboards import catalog_keyboard

CATALOG_TEXT = "У меня есть товар"
CREATE_HINT = "Пришлите фото с подписью — названием товара"
NEED_TITLE = "Добавьте название в подпись к фото"
TITLE_TOO_LONG = "Название слишком длинное (максимум 500 символов)"
CREATE_REJECTED = "Не удалось создать товар. Проверьте название и формат фото (JPEG до 10 МБ)."
NOT_ADMIN = "Добавлять товары может только администратор"
CREATED = "Товар создан"
ALREADY_EXISTS = "Такой товар уже есть"
MAX_TITLE_LENGTH = 500


def create_router(*, admin_ids: Sequence[int], public_base_url: str) -> Router:
    router = Router()
    admins = tuple(admin_ids)

    @router.message(Command("create"), F.from_user.id.in_(admins))
    @router.message(F.text == "Создать товар", F.from_user.id.in_(admins))
    async def create_product_hint(message: Message) -> None:
        await message.answer(CREATE_HINT)

    # /start и любой другой текст открывают каталог.
    @router.message(F.text)
    async def catalog(message: Message) -> None:
        await message.answer(
            CATALOG_TEXT,
            reply_markup=catalog_keyboard(public_base_url),
        )

    @router.message(F.photo & F.caption & F.from_user.id.in_(admins))
    async def admin_photo_with_caption(
        message: Message,
        bot: Bot,
        backend_client: BackendClient,
    ) -> None:
        title = (message.caption or "").strip()
        if not title:
            await message.answer(NEED_TITLE)
            return
        if len(title) > MAX_TITLE_LENGTH:
            await message.answer(TITLE_TOO_LONG)
            return

        photos = message.photo
        if not photos:
            return
        largest = photos[-1]
        buffer = BytesIO()
        await bot.download(largest, destination=buffer)
        try:
            created = await backend_client.create_product(
                title=title,
                photo_file_unique_id=largest.file_unique_id,
                image=buffer.getvalue(),
            )
        except BackendRequestError:
            await message.answer(CREATE_REJECTED)
            return
        await message.answer(CREATED if created else ALREADY_EXISTS)

    @router.message(F.photo & ~F.caption & F.from_user.id.in_(admins))
    async def admin_photo_without_caption(message: Message) -> None:
        await message.answer(NEED_TITLE)

    @router.message(F.photo)
    async def photo_from_stranger(message: Message) -> None:
        await message.answer(NOT_ADMIN)

    return router
