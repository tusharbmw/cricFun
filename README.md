# CricFun

A cricket prediction game for friends — pick match winners, apply powerups, and compete on the leaderboard.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 5.2 LTS + Django REST Framework 3.17 |
| Frontend | React 18 + Vite + Tailwind CSS v4 |
| Database | Oracle DB |
| Cache / Sessions | Redis |
| Task Queue | Celery + Celery Beat |
| Auth | JWT (djangorestframework-simplejwt) |
| Server | Gunicorn + Nginx |

## Project Structure

```
cricFun/
├── backend/          # Django REST API
│   ├── apps/
│   │   ├── picks/        # Pick placement, powerups
│   │   ├── leaderboard/  # Rankings and scores
│   │   ├── matches/      # Match data + Cricket API tasks
│   │   └── core/         # Shared utilities
│   ├── config/           # Settings (base / local / production)
│   ├── teams/            # Team and Match models
│   └── manage.py
├── frontend/         # React SPA
│   └── src/
│       ├── api/          # Axios API clients
│       ├── components/   # UI components (Card, Spinner, Badge...)
│       ├── features/     # MatchCard
│       ├── hooks/        # useCountdown
│       ├── pages/        # Dashboard, Schedule, Results, Leaderboard, Profile, Rules
│       └── store/        # Zustand auth store
├── .env.example
└── projectplan.md    # Full v2 migration plan with phase status
```

## Local Development

### Prerequisites

- Python 3.12
- Node.js 20+
- Oracle DB (dev instance)
- Redis — either via Docker or Homebrew:

```bash
# Option A — Docker (recommended, no install needed)
docker compose up -d        # starts Redis on port 6379

# Option B — Homebrew
brew install redis && brew services start redis
```

### Backend

```bash
cd backend
source ../venv/bin/activate
DJANGO_SETTINGS_MODULE=config.settings.local python manage.py runserver
```

### Frontend

```bash
cd frontend
npm install
npm run dev       # starts at http://localhost:5173
                  # /api/* proxied to http://127.0.0.1:8000
```

### Celery (optional — needed for live score updates)

```bash
cd backend
celery -A config worker -l info      # in one terminal
celery -A config beat -l info        # in another terminal
```

## Environment Variables

Copy `.env.example` to `.env` in the project root and fill in values:

```
SECRET_KEY=...
DB_NAME=...
DB_USER=...
DB_PASSWORD=...
DB_HOST=...
DB_PORT=1521
CRICKET_API_KEY=...
REDIS_URL=redis://localhost:6379/0
```

## API

- Swagger UI: `http://localhost:8000/api/v1/docs/`
- ReDoc:      `http://localhost:8000/api/v1/redoc/`
- OpenAPI:    `http://localhost:8000/api/v1/schema/`

## Production

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for the full step-by-step guide covering:
- System dependencies (Redis, Python 3.12, Node.js)
- Gunicorn systemd service setup
- Celery + Celery Beat services
- Nginx config (SPA routing + API proxy)
- SELinux settings for Oracle Linux
- SSL renewal and routine update procedure

Key commands:

```bash
# Build frontend
cd frontend && npm run build

# Collect static files
cd backend && python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate

# Renew SSL certificate
sudo certbot renew --nginx

# Oracle: grant tablespace if needed
GRANT UNLIMITED TABLESPACE TO user;
```

## Features

- **Match schedule** — pick a team to win before the pick window closes; countdown timer per match
- **Powerups** — Hidden (hide your pick), Fake (show wrong pick), No-Neg (no negative points if wrong)
- **Smart polling** — live match endpoint polled at 30s when live, 5min if match starts within 2hrs, never otherwise
- **Leaderboard** — real-time standings with win/loss/skips and points
- **Results** — completed matches with all user picks visible
- **Rules** — full scoring, powerup, and tiebreaker rules

## Testing

```bash
cd backend
pytest apps/picks/tests.py apps/leaderboard/tests.py -v
# 25 tests, 25 passing
```

Test settings use SQLite in-memory (`config.settings.test`) — no Oracle needed to run tests.

## Status

Phases 0–5 complete (backend API, React frontend, tests, code quality).
All packages on latest compatible versions — Django 5.2.12 LTS.
Next: Phase 6 (Docker) → Phase 7 (production deployment).
See [projectplan.md](projectplan.md) for detailed progress.
