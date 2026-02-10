from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import engine
from app.api.routes import router as api_router
from app.config import settings
from app.dashboard.views import router as dashboard_router

logging.basicConfig(level=logging.INFO)

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / 'static'


def _ensure_static_dir() -> Path:
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    return STATIC_DIR


@asynccontextmanager
async def lifespan(_: FastAPI):
    await engine.start()
    try:
        yield
    finally:
        await engine.market.stop()


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.include_router(api_router, prefix='/api')
    app.include_router(dashboard_router)
    app.mount('/static', StaticFiles(directory=str(_ensure_static_dir())), name='static')
    return app


app = create_app()
