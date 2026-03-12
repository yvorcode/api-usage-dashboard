from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from google.cloud import monitoring_v3
from google.protobuf.duration_pb2 import Duration

from backend.config import Settings


class GoogleService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def fetch_usage(self) -> Dict[str, Any]:
        if not self.settings.google_enabled:
            return self._empty_response('not_configured', 'Not configured - set Google Cloud env vars to enable')

        try:
            self.settings.ensure_google_credentials_file()
            client = monitoring_v3.MetricServiceClient()
            project_name = f'projects/{self.settings.google_cloud_project_id}'

            now = datetime.now(timezone.utc)
            interval = monitoring_v3.TimeInterval(
                end_time=now,
                start_time=now - timedelta(days=30),
            )
            aggregation = monitoring_v3.Aggregation(
                alignment_period=Duration(seconds=86400),
                per_series_aligner=monitoring_v3.Aggregation.Aligner.ALIGN_SUM,
                cross_series_reducer=monitoring_v3.Aggregation.Reducer.REDUCE_SUM,
                group_by_fields=['metric.labels.service', 'metric.labels.response_code_class'],
            )
            series = client.list_time_series(
                request={
                    'name': project_name,
                    'filter': 'metric.type="serviceruntime.googleapis.com/api/request_count"',
                    'interval': interval,
                    'view': monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
                    'aggregation': aggregation,
                }
            )
            return self._transform_series(series)
        except Exception as exc:  # noqa: BLE001
            return self._empty_response('error', f'Unable to fetch data - {exc}')

    def _transform_series(self, series: Any) -> Dict[str, Any]:
        services: Dict[str, Dict[str, float]] = defaultdict(lambda: {'requests': 0, 'errors': 0})

        for item in series:
            labels = item.metric.labels
            service_name = labels.get('service', 'unknown')
            response_class = labels.get('response_code_class', 'unknown')
            total = 0
            for point in item.points:
                value = getattr(point.value, 'int64_value', 0) or getattr(point.value, 'double_value', 0)
                total += int(value)
            services[service_name]['requests'] += total
            if str(response_class).startswith('5') or str(response_class).startswith('4'):
                services[service_name]['errors'] += total

        rows: List[Dict[str, Any]] = []
        for service, values in sorted(services.items(), key=lambda item: item[1]['requests'], reverse=True):
            requests = int(values['requests'])
            errors = int(values['errors'])
            error_rate = round((errors / requests * 100) if requests else 0.0, 2)
            rows.append({
                'service': service,
                'requests': requests,
                'errors': errors,
                'error_rate': error_rate,
            })

        total_requests = sum(row['requests'] for row in rows)
        total_errors = sum(row['errors'] for row in rows)
        avg_error_rate = round((total_errors / total_requests * 100) if total_requests else 0.0, 2)

        return {
            'service': 'google',
            'status': 'connected',
            'message': None,
            'lookback_days': 30,
            'totals': {
                'requests': total_requests,
                'errors': total_errors,
                'error_rate': avg_error_rate,
            },
            'services': rows,
            'top_services': rows[:5],
        }

    def _empty_response(self, status: str, message: str) -> Dict[str, Any]:
        return {
            'service': 'google',
            'status': status,
            'message': message,
            'lookback_days': 30,
            'totals': {
                'requests': 0,
                'errors': 0,
                'error_rate': 0.0,
            },
            'services': [],
            'top_services': [],
        }
