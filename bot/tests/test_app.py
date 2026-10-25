from pathlib import Path

import pytest
from aiohttp.test_utils import TestClient, TestServer

from app.main import create_app
from app.settings import Settings


def test_admin_ids_are_split() -> None:
    settings = Settings(
        bot_token="123456:test-token",
        webhook_secret="secret",
        admin_ids="10, 20,30",
        public_base_url="http://localhost",
        service_token="svc",
        backend_internal_url="http://backend:8000",
    )
    assert settings.admin_id_list() == (10, 20, 30)


def test_package_does_not_poll_or_keep_fsm_storage() -> None:
    root = Path(__file__).resolve().parents[1] / "app"
    source = "\n".join(path.read_text(encoding="utf-8") for path in sorted(root.rglob("*.py")))
    for token in ("MemoryStorage", "start_polling", "run_polling", "tempfile", "lru_cache"):
        assert token not in source
    main = (root / "main.py").read_text(encoding="utf-8")
    assert "set_webhook" not in main
    assert "disable_fsm=True" in main


async def test_health_and_webhook_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BOT_TOKEN", "123456:test-token")
    monkeypatch.setenv("WEBHOOK_SECRET", "test-secret")
    monkeypatch.setenv("ADMIN_IDS", "10")
    monkeypatch.setenv("PUBLIC_BASE_URL", "http://localhost")
    monkeypatch.setenv("SERVICE_TOKEN", "svc")
    monkeypatch.setenv("BACKEND_INTERNAL_URL", "http://backend:8000")

    application = create_app()
    async with TestClient(TestServer(application)) as client:
        health = await client.get("/health")
        assert health.status == 200
        assert await health.json() == {"status": "ok"}

        rejected = await client.post("/bot/webhook", json={"update_id": 1})
        assert rejected.status == 401
