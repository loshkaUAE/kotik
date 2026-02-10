from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()


def _templates_dir() -> Path:
    # Stable absolute path regardless of current working directory.
    return Path(__file__).resolve().parent.parent / 'templates'


templates = Jinja2Templates(directory=str(_templates_dir()))


@router.get('/', response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse('index.html', {'request': request})
