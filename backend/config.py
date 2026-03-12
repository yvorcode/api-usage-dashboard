from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import Field, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    anthropic_api_key: Optional[str] = Field(default=None, alias='ANTHROPIC_API_KEY')
    port: int = Field(default=8080, alias='PORT')
    cache_ttl_seconds: int = Field(default=900, alias='CACHE_TTL_SECONDS')
    anthropic_lookback_days: int = Field(default=30, alias='ANTHROPIC_LOOKBACK_DAYS')

    @model_validator(mode='after')
    def validate_values(self) -> 'Settings':
        if self.port <= 0:
            raise ValueError('PORT must be a positive integer')
        if self.cache_ttl_seconds <= 0:
            raise ValueError('CACHE_TTL_SECONDS must be a positive integer')
        if self.anthropic_lookback_days <= 0:
            raise ValueError('ANTHROPIC_LOOKBACK_DAYS must be a positive integer')
        return self

    @computed_field  # type: ignore[misc]
    @property
    def anthropic_enabled(self) -> bool:
        return bool(self.anthropic_api_key)

    @computed_field  # type: ignore[misc]
    @property
    def google_enabled(self) -> bool:
        return True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
