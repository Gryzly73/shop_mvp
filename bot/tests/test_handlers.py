from datetime import UTC, datetime
from unittest.mock import AsyncMock

from aiogram import Bot, Dispatcher
from aiogram.methods import GetFile, SendMessage
from aiogram.types import (
    Chat,
    InlineKeyboardMarkup,
    Message,
    MessageEntity,
    PhotoSize,
    Update,
    User,
)

from app.backend_client import BackendRequestError
from app.handlers import (
    ALREADY_EXISTS,
    CATALOG_TEXT,
    CREATE_HINT,
    CREATE_REJECTED,
    CREATED,
    MAX_TITLE_LENGTH,
    NEED_TITLE,
    NOT_ADMIN,
    TITLE_TOO_LONG,
    create_router,
)
from tests.fakes import FakeSession

ADMIN_ID = 10
OTHER_ID = 20
PUBLIC_URL = "http://localhost"


def _user(user_id: int) -> User:
    return User(id=user_id, is_bot=False, first_name="Ann")


def _text(user_id: int, text: str, *, command: bool = False) -> Message:
    entities = None
    if command:
        entities = [MessageEntity(type="bot_command", offset=0, length=len(text.split()[0]))]
    return Message(
        message_id=1,
        date=datetime.now(UTC),
        chat=Chat(id=100, type="private"),
        from_user=_user(user_id),
        text=text,
        entities=entities,
    )


def _photo(user_id: int, caption: str | None) -> Message:
    return Message(
        message_id=1,
        date=datetime.now(UTC),
        chat=Chat(id=100, type="private"),
        from_user=_user(user_id),
        photo=[
            PhotoSize(file_id="small", file_unique_id="uniq-small", width=10, height=10),
            PhotoSize(file_id="big", file_unique_id="uniq-big", width=100, height=100),
        ],
        caption=caption,
    )


async def _dispatch(
    message: Message,
    backend: AsyncMock | None = None,
) -> tuple[FakeSession, AsyncMock]:
    session = FakeSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(create_router(admin_ids=(ADMIN_ID,), public_base_url=PUBLIC_URL))
    client = backend if backend is not None else AsyncMock()
    try:
        await dispatcher.feed_update(
            bot,
            Update(update_id=1, message=message),
            backend_client=client,
        )
    finally:
        await session.close()
    return session, client


def _answers(session: FakeSession) -> list[SendMessage]:
    return [call for call in session.calls if isinstance(call, SendMessage)]


async def test_start_and_any_text_open_catalog() -> None:
    for text in ("/start", "привет"):
        session, backend = await _dispatch(_text(OTHER_ID, text, command=text.startswith("/")))
        answers = _answers(session)
        assert len(answers) == 1
        assert answers[0].text == CATALOG_TEXT
        markup = answers[0].reply_markup
        assert isinstance(markup, InlineKeyboardMarkup)
        button = markup.inline_keyboard[0][0]
        assert button.web_app is not None
        assert button.web_app.url == PUBLIC_URL
        backend.create_product.assert_not_awaited()


async def test_admin_create_command_asks_for_a_captioned_photo() -> None:
    for message in (
        _text(ADMIN_ID, "/create", command=True),
        _text(ADMIN_ID, "Создать товар"),
    ):
        session, backend = await _dispatch(message)
        answers = _answers(session)
        assert len(answers) == 1
        assert answers[0].text == CREATE_HINT
        assert answers[0].reply_markup is None
        backend.create_product.assert_not_awaited()


async def test_create_command_from_stranger_opens_catalog() -> None:
    session, backend = await _dispatch(_text(OTHER_ID, "/create", command=True))
    answers = _answers(session)
    assert answers[0].text == CATALOG_TEXT
    backend.create_product.assert_not_awaited()


async def test_admin_photo_with_caption_creates_product() -> None:
    backend = AsyncMock()
    backend.create_product.return_value = True
    session, _backend = await _dispatch(_photo(ADMIN_ID, "  Кружка  "), backend)

    backend.create_product.assert_awaited_once_with(
        title="Кружка",
        photo_file_unique_id="uniq-big",
        image=b"jpeg-bytes",
    )
    assert isinstance(session.calls[0], GetFile)
    assert session.calls[0].file_id == "big"
    assert _answers(session)[0].text == CREATED


async def test_duplicate_photo_is_reported() -> None:
    backend = AsyncMock()
    backend.create_product.return_value = False
    session, _backend = await _dispatch(_photo(ADMIN_ID, "Кружка"), backend)
    assert _answers(session)[0].text == ALREADY_EXISTS


async def test_photo_from_stranger_is_rejected() -> None:
    backend = AsyncMock()
    session, _backend = await _dispatch(_photo(OTHER_ID, "Кружка"), backend)
    assert _answers(session)[0].text == NOT_ADMIN
    assert not any(isinstance(call, GetFile) for call in session.calls)
    backend.create_product.assert_not_awaited()


async def test_admin_photo_without_caption_asks_for_a_title() -> None:
    backend = AsyncMock()
    session, _backend = await _dispatch(_photo(ADMIN_ID, None), backend)
    assert _answers(session)[0].text == NEED_TITLE
    assert not any(isinstance(call, GetFile) for call in session.calls)
    backend.create_product.assert_not_awaited()


async def test_admin_photo_with_blank_caption_asks_for_a_title() -> None:
    backend = AsyncMock()
    session, _backend = await _dispatch(_photo(ADMIN_ID, "   "), backend)
    assert _answers(session)[0].text == NEED_TITLE
    backend.create_product.assert_not_awaited()


async def test_admin_photo_with_long_caption_is_rejected_before_download() -> None:
    backend = AsyncMock()
    session, _backend = await _dispatch(_photo(ADMIN_ID, "x" * (MAX_TITLE_LENGTH + 1)), backend)
    assert _answers(session)[0].text == TITLE_TOO_LONG
    assert not any(isinstance(call, GetFile) for call in session.calls)
    backend.create_product.assert_not_awaited()


async def test_backend_client_error_is_reported_without_raising() -> None:
    backend = AsyncMock()
    backend.create_product.side_effect = BackendRequestError(422, "title is empty")
    session, _backend = await _dispatch(_photo(ADMIN_ID, "Кружка"), backend)
    assert _answers(session)[0].text == CREATE_REJECTED
