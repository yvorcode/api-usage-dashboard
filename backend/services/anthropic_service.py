from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any, Dict, List

import httpx

from backend.config import Settings

PRICING = {
    'claude-opus-4': {'input': 15.00, 'output': 75.00},
    'claude-sonnet-4-6': {'input': 3.00, 'output': 15.00},
    'claude-haiku-4': {'input': 0.80, 'output': 4.00},
}

MODEL_ALIASES = {
    'claude-4-opus': 'claude-opus-4',
    'claude-4-sonnet': 'claude-sonnet-4-6',
    'claude-4-haiku': 'claude-haiku-4',
}


class AnthropicService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def fetch_usage(self) -> Dict[str, Any]:
        if not self.settings.anthropic_enabled:
            return self._empty_response('not_configured', 'Not configured - set ANTHROPIC_API_KEY to enable')

        end_date = date.today()
        start_date = end_date - timedelta(days=self.settings.anthropic_lookback_days - 1)
        url = 'https://api.anthropic.com/v1/usage/daily'
        params = {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
        }
        headers = {
            'x-api-key': self.settings.anthropic_api_key or '',
            'anthropic-version': '2023-06-01',
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
            payload = response.json()
            return self._transform_payload(payload, start_date, end_date)
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500]
            return self._empty_response('error', f'Unable to fetch data - {exc.response.status_code}: {detail}')
        except Exception as exc:  # noqa: BLE001
            return self._empty_response('error', f'Unable to fetch data - {exc}')

    def _transform_payload(self, payload: Dict[str, Any], start_date: date, end_date: date) -> Dict[str, Any]:
        data = payload.get('data', []) if isinstance(payload, dict) else []
        per_model: Dict[str, Dict[str, float]] = defaultdict(lambda: {'input_tokens': 0, 'output_tokens': 0, 'cost_usd': 0.0})
        daily_map: Dict[str, Dict[str, float]] = defaultdict(lambda: {'input_tokens': 0, 'output_tokens': 0})
        request_count = 0

        for item in data:
            model_raw = item.get('model', 'unknown')
            model = MODEL_ALIASES.get(model_raw, model_raw)
            input_tokens = int(item.get('input_tokens', 0) or 0)
            output_tokens = int(item.get('output_tokens', 0) or 0)
            requests = int(item.get('request_count', item.get('requests', 0)) or 0)
            usage_date = item.get('date') or item.get('usage_date') or start_date.isoformat()
            cost = self._estimate_cost(model, input_tokens, output_tokens)

            per_model[model]['input_tokens'] += input_tokens
            per_model[model]['output_tokens'] += output_tokens
            per_model[model]['cost_usd'] += cost
            daily_map[usage_date]['input_tokens'] += input_tokens
            daily_map[usage_date]['output_tokens'] += output_tokens
            request_count += requests

        daily = []
        current = start_date
        while current <= end_date:
            day_key = current.isoformat()
            day = daily_map[day_key]
            daily.append({
                'date': day_key,
                'input_tokens': int(day['input_tokens']),
                'output_tokens': int(day['output_tokens']),
            })
            current += timedelta(days=1)

        models = [
            {
                'model': model,
                'input_tokens': int(values['input_tokens']),
                'output_tokens': int(values['output_tokens']),
                'cost_usd': round(values['cost_usd'], 4),
            }
            for model, values in sorted(per_model.items(), key=lambda item: item[1]['input_tokens'] + item[1]['output_tokens'], reverse=True)
        ]

        total_input = sum(item['input_tokens'] for item in models)
        total_output = sum(item['output_tokens'] for item in models)
        total_cost = round(sum(item['cost_usd'] for item in models), 4)

        return {
            'service': 'anthropic',
            'status': 'connected',
            'message': None,
            'request_count': request_count,
            'lookback_days': self.settings.anthropic_lookback_days,
            'totals': {
                'input_tokens': total_input,
                'output_tokens': total_output,
                'total_tokens': total_input + total_output,
                'cost_usd': total_cost,
            },
            'models': models,
            'daily': daily,
        }

    def _estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        pricing = PRICING.get(model)
        if not pricing:
            return 0.0
        return (input_tokens / 1_000_000 * pricing['input']) + (output_tokens / 1_000_000 * pricing['output'])

    def _empty_response(self, status: str, message: str) -> Dict[str, Any]:
        return {
            'service': 'anthropic',
            'status': status,
            'message': message,
            'request_count': 0,
            'lookback_days': self.settings.anthropic_lookback_days,
            'totals': {
                'input_tokens': 0,
                'output_tokens': 0,
                'total_tokens': 0,
                'cost_usd': 0.0,
            },
            'models': [],
            'daily': [],
        }
