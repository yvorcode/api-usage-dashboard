from __future__ import annotations

from typing import Any, Dict, List

from backend.config import Settings


MOCK_SERVICES: List[Dict[str, Any]] = [
    {'service': 'generativelanguage.googleapis.com', 'requests': 1843200, 'errors': 11245},
    {'service': 'aiplatform.googleapis.com', 'requests': 1398420, 'errors': 7340},
    {'service': 'storage.googleapis.com', 'requests': 965410, 'errors': 1890},
    {'service': 'run.googleapis.com', 'requests': 621775, 'errors': 2784},
    {'service': 'bigquery.googleapis.com', 'requests': 487230, 'errors': 960},
    {'service': 'secretmanager.googleapis.com', 'requests': 211890, 'errors': 306},
    {'service': 'artifactregistry.googleapis.com', 'requests': 154440, 'errors': 188},
    {'service': 'cloudbuild.googleapis.com', 'requests': 98410, 'errors': 144},
]


class GoogleService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def fetch_usage(self) -> Dict[str, Any]:
        rows = []
        for item in MOCK_SERVICES:
            requests = int(item['requests'])
            errors = int(item['errors'])
            error_rate = round((errors / requests * 100) if requests else 0.0, 2)
            rows.append(
                {
                    'service': item['service'],
                    'requests': requests,
                    'errors': errors,
                    'error_rate': error_rate,
                }
            )

        total_requests = sum(row['requests'] for row in rows)
        total_errors = sum(row['errors'] for row in rows)
        avg_error_rate = round((total_errors / total_requests * 100) if total_requests else 0.0, 2)

        return {
            'service': 'google',
            'status': 'connected',
            'message': 'Mock data',
            'lookback_days': 30,
            'mocked': True,
            'totals': {
                'requests': total_requests,
                'errors': total_errors,
                'error_rate': avg_error_rate,
            },
            'services': rows,
            'top_services': rows[:5],
        }
