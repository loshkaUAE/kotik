from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import engine
from app.api.routes import router as api_router
from app.config import settings
from app.dashboard.views import router as dashboard_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(title=settings.app_name)
app.include_router(api_router, prefix='/api')
app.include_router(dashboard_router)
app.mount('/static', StaticFiles(directory='app/static'), name='static')


@app.on_event('startup')
async def startup() -> None:
    await engine.start()
