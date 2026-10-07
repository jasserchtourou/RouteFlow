import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import configure_mappers

from app import models as _models  # noqa: F401  (registers every model so relationships resolve)
from app.api.v1.router import api_v1_router
from app.core.config import Settings, get_settings
from app.core.database import create_engine, create_session_factory
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import REQUEST_ID_HEADER, RequestContextMiddleware

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory: builds a fully configured app from explicit settings.

    Tests call this with their own Settings instead of patching globals.
    """
    settings = settings or get_settings()
    configure_logging(settings.log_level, json_logs=settings.is_production)
    # Resolve all ORM relationships now: a broken model fails at startup, not on the first
    # request that happens to touch it.
    configure_mappers()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Startup: create the process-wide engine + session factory.
        engine = create_engine(settings)
        app.state.engine = engine
        app.state.session_factory = create_session_factory(engine)
        logger.info("%s started (env=%s)", settings.app_name, settings.app_env)
        yield
        # Shutdown: close pooled connections cleanly.
        await engine.dispose()
        logger.info("%s stopped", settings.app_name)

    app = FastAPI(
        title=f"{settings.app_name} API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
    )

    # Middleware order: the last added is the outermost. CORS must be outermost so that
    # even error responses carry CORS headers.
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[REQUEST_ID_HEADER],
    )

    register_exception_handlers(app)
    app.include_router(api_v1_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
