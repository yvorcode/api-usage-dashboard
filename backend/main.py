from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.cache import TTLCache
from backend.config import get_settings
from backend.routers import anthropic, google
from backend.scheduler import RefreshScheduler

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / 'frontend'


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    cache = TTLCache(ttl_seconds=settings.cache_ttl_seconds)
    scheduler = RefreshScheduler(cache=cache, settings=settings)

    app.state.settings = settings
    app.state.cache = cache
    app.state.scheduler = scheduler

    await scheduler.refresh_all()
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown()


app = FastAPI(title='API Usage Dashboard', lifespan=lifespan)
app.include_router(anthropic.router)
app.include_router(google.router)
app.mount('/static', StaticFiles(directory=str(FRONTEND_DIR)), name='static')


@app.get('/api/status')
async def get_status():
    settings = get_settings()
    cache = app.state.cache
    anthropic_payload = cache.get('anthropic') or {
        'status': 'not_loaded',
        'message': 'No data loaded yet',
    }
    google_payload = cache.get('google') or {
        'status': 'not_loaded',
        'message': 'No data loaded yet',
    }
    return {
        'status': 'ok',
        'cache_ttl_seconds': settings.cache_ttl_seconds,
        'services': {
            'anthropic': {
                'enabled': settings.anthropic_enabled,
                'cache_age_seconds': cache.age_seconds('anthropic'),
                'status': anthropic_payload.get('status'),
                'message': anthropic_payload.get('message'),
            },
            'google': {
                'enabled': settings.google_enabled,
                'cache_age_seconds': cache.age_seconds('google'),
                'status': google_payload.get('status'),
                'message': google_payload.get('message'),
            },
        },
    }


@app.get('/')
async def index():
    return FileResponse(FRONTEND_DIR / 'index.html')
