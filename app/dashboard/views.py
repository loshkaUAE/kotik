from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / 'templates'
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get('/', response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse('index.html', {'request': request})
