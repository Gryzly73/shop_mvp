import socket
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import aioboto3
from fastapi import FastAPI, Request, Response
from sqlalchemy.ext.asyncio import AsyncEngine
from starlette.middleware.base import RequestResponseEndpoint

from app.api.routes_internal import router as internal_router
from app.api.routes_public import router as public_router
from app.infrastructure.db import create_db_engine, create_session_factory
from app.infrastructure.settings import load_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = load_settings()
    engine: AsyncEngine = create_db_engine(settings.sqlalchemy_url())
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    app.state.s3_session = aioboto3.Session()
    try:
        yield
    finally:
        await engine.dispose()


def create_app() -> FastAPI:
    application = FastAPI(lifespan=lifespan)

    @application.middleware("http")
    async def instance_header(
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Instance"] = socket.gethostname()
        return response

    application.include_router(public_router)
    application.include_router(internal_router)
    return application


app = create_app()
