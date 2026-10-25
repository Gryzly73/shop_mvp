from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.methods import GetFile, SendMessage, SetChatMenuButton, SetWebhook, TelegramMethod
from aiogram.methods.base import TelegramType
from aiogram.types import Chat, File, Message


class FakeSession(BaseSession):
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[TelegramMethod[Any]] = []
        self.file_bytes = b"jpeg-bytes"

    async def close(self) -> None:
        return None

    async def make_request(
        self,
        bot: Bot,
        method: TelegramMethod[TelegramType],
        timeout: int | None = None,
    ) -> TelegramType:
        self.calls.append(method)
        if isinstance(method, SendMessage):
            chat_id = method.chat_id if isinstance(method.chat_id, int) else 1
            return Message(
                message_id=2,
                date=datetime.now(UTC),
                chat=Chat(id=chat_id, type="private"),
                text=method.text,
            )
        if isinstance(method, GetFile):
            return File(
                file_id=method.file_id,
                file_unique_id="downloaded",
                file_path="photos/file.jpg",
            )
        if isinstance(method, SetWebhook | SetChatMenuButton):
            return True
        raise AssertionError(f"unexpected method {type(method).__name__}")

    async def stream_content(
        self,
        url: str,
        headers: dict[str, Any] | None = None,
        timeout: int = 30,
        chunk_size: int = 65536,
        raise_for_status: bool = True,
    ) -> AsyncGenerator[bytes, None]:
        yield self.file_bytes
