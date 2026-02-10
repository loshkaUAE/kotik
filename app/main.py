from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as api_router
from app.api.routes import runtime
from app.config import settings
from app.dashboard.views import router as dashboard_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    await runtime.start()
    try:
        yield
    finally:
        await runtime.stop()


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    static_dir = Path(__file__).resolve().parent / 'static'
    static_dir.mkdir(parents=True, exist_ok=True)
    app.mount('/static', StaticFiles(directory=str(static_dir)), name='static')
    app.include_router(api_router, prefix='/api')
    app.include_router(dashboard_router)
    return app


app = create_app()
