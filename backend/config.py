from __future__ import annotations

import json
import os
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    anthropic_api_key: Optional[str] = Field(default=None, alias='ANTHROPIC_API_KEY')
    google_application_credentials_json: Optional[str] = Field(default=None, alias='GOOGLE_APPLICATION_CREDENTIALS_JSON')
    google_cloud_project_id: Optional[str] = Field(default=None, alias='GOOGLE_CLOUD_PROJECT_ID')
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
        if self.google_application_credentials_json and not self.google_cloud_project_id:
            raise ValueError('GOOGLE_CLOUD_PROJECT_ID is required when GOOGLE_APPLICATION_CREDENTIALS_JSON is set')
        if self.google_cloud_project_id and not self.google_application_credentials_json:
            raise ValueError('GOOGLE_APPLICATION_CREDENTIALS_JSON is required when GOOGLE_CLOUD_PROJECT_ID is set')
        if self.google_application_credentials_json:
            try:
                parsed = json.loads(self.google_application_credentials_json)
            except json.JSONDecodeError as exc:
                raise ValueError('GOOGLE_APPLICATION_CREDENTIALS_JSON must be valid JSON') from exc
            if not isinstance(parsed, dict):
                raise ValueError('GOOGLE_APPLICATION_CREDENTIALS_JSON must decode to a JSON object')
            if 'client_email' not in parsed or 'private_key' not in parsed:
                raise ValueError('GOOGLE_APPLICATION_CREDENTIALS_JSON must include client_email and private_key')
        return self

    @computed_field  # type: ignore[misc]
    @property
    def anthropic_enabled(self) -> bool:
        return bool(self.anthropic_api_key)

    @computed_field  # type: ignore[misc]
    @property
    def google_enabled(self) -> bool:
        return bool(self.google_application_credentials_json and self.google_cloud_project_id)

    def ensure_google_credentials_file(self) -> Optional[str]:
        if not self.google_enabled or not self.google_application_credentials_json:
            return None
        current = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        if current and Path(current).exists():
            return current
        fd, path = tempfile.mkstemp(prefix='gcp-sa-', suffix='.json')
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            handle.write(self.google_application_credentials_json)
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = path
        return path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
