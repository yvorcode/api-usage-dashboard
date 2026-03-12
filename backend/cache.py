from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class CacheEntry:
    value: Any
    stored_at: float
    expires_at: float


class TTLCache:
    def __init__(self, ttl_seconds: int) -> None:
        self.ttl_seconds = ttl_seconds
        self._data: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._data.get(key)
            if not entry:
                return None
            if entry.expires_at < time.time():
                self._data.pop(key, None)
                return None
            return entry.value

    def get_entry(self, key: str) -> Optional[CacheEntry]:
        with self._lock:
            entry = self._data.get(key)
            if not entry:
                return None
            if entry.expires_at < time.time():
                self._data.pop(key, None)
                return None
            return entry

    def set(self, key: str, value: Any) -> CacheEntry:
        now = time.time()
        entry = CacheEntry(value=value, stored_at=now, expires_at=now + self.ttl_seconds)
        with self._lock:
            self._data[key] = entry
        return entry

    def force_refresh(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)

    def age_seconds(self, key: str) -> Optional[float]:
        entry = self.get_entry(key)
        if not entry:
            return None
        return max(0.0, time.time() - entry.stored_at)
