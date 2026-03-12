from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from backend.cache import TTLCache
from backend.config import Settings
from backend.services.anthropic_service import AnthropicService
from backend.services.google_service import GoogleService


class RefreshScheduler:
    def __init__(self, cache: TTLCache, settings: Settings) -> None:
        self.cache = cache
        self.settings = settings
        self.scheduler = AsyncIOScheduler()
        self.anthropic_service = AnthropicService(settings)
        self.google_service = GoogleService(settings)

    async def refresh_anthropic(self) -> None:
        self.cache.set('anthropic', await self.anthropic_service.fetch_usage())

    async def refresh_google(self) -> None:
        self.cache.set('google', await self.google_service.fetch_usage())

    async def refresh_all(self) -> None:
        await self.refresh_anthropic()
        await self.refresh_google()

    def start(self) -> None:
        self.scheduler.add_job(self.refresh_anthropic, 'interval', minutes=15, id='anthropic-refresh', replace_existing=True)
        self.scheduler.add_job(self.refresh_google, 'interval', minutes=15, id='google-refresh', replace_existing=True)
        self.scheduler.start()

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
