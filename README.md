# API Usage Dashboard — PoC

Self-hosted, dockerized dashboard showing API usage across Anthropic and Google Cloud with no external database or cache.

## Features

- FastAPI backend with static frontend mount
- In-process TTL cache
- APScheduler background refresh every 15 minutes
- Anthropic usage endpoint integration with cost estimation
- Google Cloud Monitoring integration for API request count / error rate
- Vanilla HTML/CSS/JS frontend with Chart.js
- Graceful partial configuration: works with one service enabled
- Manual refresh support

## Supported Services

| Service | Metrics |
|---|---|
| Anthropic (Claude) | Token usage per model, cost estimate, request count, daily breakdown |
| Google Cloud APIs | Request count per API service, quota-adjacent request usage, error rate |

## Environment Variables

```env
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_APPLICATION_CREDENTIALS_JSON={"type":"service_account",...}
GOOGLE_CLOUD_PROJECT_ID=my-gcp-project
PORT=8080
CACHE_TTL_SECONDS=900
ANTHROPIC_LOOKBACK_DAYS=30
```

`GOOGLE_APPLICATION_CREDENTIALS_JSON` is written to a temporary file on startup and exported through `GOOGLE_APPLICATION_CREDENTIALS` automatically.

## Run locally

### Docker Compose

```bash
cp .env.example .env
# edit .env
docker-compose up --build
```

Dashboard: <http://localhost:8080>

### Without Docker

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8080
```

## Endpoints

- `GET /api/usage/anthropic`
- `GET /api/usage/google`
- `GET /api/status`
- Append `?refresh=true` to either usage endpoint for a manual refresh

## Notes

### Anthropic

Uses `GET https://api.anthropic.com/v1/usage/daily` with `start_date` / `end_date` and `anthropic-version: 2023-06-01`.

Pricing estimates are based on the models listed in the spec. Unknown models are included in token totals but priced at `0` until mapped.

### Google Cloud

Uses `google-cloud-monitoring` against:

- `metric.type="serviceruntime.googleapis.com/api/request_count"`
- grouped by service name and response code class
- summed daily over the last 30 days

Required IAM:

- `roles/monitoring.viewer`
- `roles/serviceusage.serviceUsageConsumer`

## Project Structure

```text
api-usage-dashboard/
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── README.md
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── cache.py
│   ├── scheduler.py
│   ├── config.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── anthropic.py
│   │   └── google.py
│   └── services/
│       ├── __init__.py
│       ├── anthropic_service.py
│       └── google_service.py
└── frontend/
    ├── index.html
    ├── style.css
    └── app.js
```

## Design decisions

- No external stateful dependency: simpler deploy and PoC-friendly
- Cache can store error payloads too, so bad credentials show clear UI state instead of crashing the app
- Frontend is framework-free to keep the container small and deployment trivial

## Known limitations

- Anthropic response parsing is defensive but may need minor field mapping updates if the upstream schema changes
- Google Cloud section reports request/error metrics from Monitoring, but does not yet surface quota limit values directly
- No auth layer is included; this is intended for trusted self-hosted environments
