# RealGrowth Data Service

RealGrowth Data Service is a FastAPI application that searches and enriches prospects using Apollo and Clay, searches companies with Google Maps, tracks prospect connections, and processes uploaded conversation screenshots.

## Requirements

- Python 3.10 or later (the code uses Python 3.10+ type syntax)
- MongoDB, reachable at the URI configured in `.env`
- RabbitMQ, reachable at the URL configured in `.env` (the API connects to it during startup)
- Redis for asynchronous conversation-analysis jobs (the Celery worker uses it)
- API credentials for the integrations you plan to use

The application does not include a Docker Compose file. Start MongoDB, RabbitMQ, and Redis separately, or use your team's existing instances.

## Setup

Run these commands from the repository root. On Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

If PowerShell blocks activation, either enable script execution for your user or invoke the environment's Python directly with `.\.venv\Scripts\python.exe`.

On macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

## Configuration

Edit `.env` and replace placeholder values with credentials and service locations. `app/config/settings.py` requires these settings to be present when the app starts:

| Variable | Purpose |
| --- | --- |
| `APOLLO_API_KEY` | Apollo people search and enrichment |
| `CLAY_API_KEY` | Clay search |
| `GOOGLE_MAPS_API_KEY` | Google Maps company search |
| `MONGODB_URI` | MongoDB connection string |
| `MONGODB_DATABASE` | Database name |
| `PROSPECT_PROCESSING_API_KEY` | API key sent to the NestJS prospect-processing backend |
| `HUGGINGFACE_API_TOKEN` | Hugging Face OCR integration configuration |
| `GROQ_API_KEY` | OCR fallback and conversation analysis |

Other settings, including the NestJS URL, MongoDB collection names, queue names, model IDs, and Cloudinary configuration, are shown in `.env.example`. Cloudinary credentials are needed for screenshot storage. Tesseract is optional; install the Tesseract OCR executable and set `TESSERACT_CMD` if using that OCR path.

Service defaults in the settings are `mongodb://localhost:27017`, RabbitMQ at `amqp://guest:guest@localhost:5672/`, and Redis at `redis://localhost:6380` (databases 0 and 1). Ensure the services are available at the configured addresses. Override these values in `.env` when needed. The app must be able to connect to MongoDB and RabbitMQ before its API server finishes starting.

## Run the API

With the virtual environment active and `.env` configured:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The `PORT` value in `.env` is not read by the Uvicorn command above; pass a different port using `--port` if needed. For example, `uvicorn app.main:app --reload --port 8010`.

When startup succeeds, open:

- Health check: <http://127.0.0.1:8000/health>
- Interactive API docs: <http://127.0.0.1:8000/docs>
- OpenAPI schema: <http://127.0.0.1:8000/openapi.json>

## Run the background worker

Conversation analysis is queued in Celery. Start a worker in a second terminal from the repository root, using the same virtual environment and `.env` configuration:

```bash
celery -A app.celery_app:celery_app worker --loglevel=info
```

On Windows, Celery's default prefork pool may not work reliably. Use the solo pool for local development:

```powershell
celery -A app.celery_app:celery_app worker --loglevel=info --pool=solo
```

The worker needs Redis configured by `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND`. These settings are optional in `.env`; the application defaults to Redis on port 6380. Starting the API alone does not run the worker.

## API areas

Use `/docs` to see the request and response schemas. Main route groups are:

- `GET /health`
- `POST /api/v1/apollo/people/search`
- `POST /api/v1/apollo/people/enrich`
- `GET /api/v1/clay/people/search/fields`
- `POST /api/v1/clay/people/search`
- `POST /api/v1/google-maps/companies/search`
- `/api/v1/connections` for prospect connection tracking
- `/api/v1/conversations` for screenshot upload and conversation retrieval

Requests to provider endpoints use the configured third-party services and may incur usage or billing under those accounts.

## Troubleshooting

- **Settings validation error at import/startup:** check that `.env` exists and all required variables listed above have values.
- **API startup cannot connect:** verify MongoDB and RabbitMQ are running and their `.env` URLs are reachable. RabbitMQ must be available even if you only intend to use the health endpoint because it connects during application startup.
- **Conversation jobs remain pending:** verify Redis is reachable at the configured Celery broker URL and that the Celery worker is running.
- **Provider request fails:** verify the relevant API key, network access, and provider account limits.
- **Screenshot upload fails:** check Cloudinary configuration and that the API server can reach Cloudinary. For local OCR, also verify Tesseract installation and `TESSERACT_CMD`.

## Tests

Run the test suite from the repository root:

```bash
python -m pytest
```
