# CricFun

A cricket prediction game for friends — pick match winners, apply powerups, and compete on the leaderboard.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 5.2 LTS + Django REST Framework |
| Frontend | React 19 + Vite + Tailwind CSS v4 |
| Database | Oracle DB |
| Cache / Sessions | Redis |
| Task Queue | Celery + Celery Beat |
| Auth | JWT (djangorestframework-simplejwt) + Google OAuth |
| Charts | Recharts |
| Server | Gunicorn + Nginx |
| CI/CD | GitHub Actions |

## Project Structure

```
cricFun/
├── backend/          # Django REST API
│   ├── apps/
│   │   ├── core/         # SiteSettings, CricAPI client, shared utilities
│   │   ├── leaderboard/  # Rankings, scores, snapshots, history
│   │   ├── matches/      # Match data, Cricket API polling tasks
│   │   ├── notifications/ # In-app notifications, rank-change alerts
│   │   ├── picks/        # Pick placement, powerups
│   │   └── users/        # User profiles
│   ├── config/           # Settings (base / local / production / test)
│   ├── teams/            # Team and Match models
│   └── manage.py
├── frontend/         # React SPA
│   └── src/
│       ├── api/          # Axios API clients
│       ├── components/   # UI components (layout, cards, spinner...)
│       ├── pages/        # Dashboard, Schedule, Results, Leaderboard, Profile, Rules, MatchDetail
│       └── store/        # Zustand auth store
├── .env.example
└── docs/
    └── DEPLOYMENT.md     # Full production deployment guide
```

## Local Development

### Prerequisites

- Python 3.12
- Node.js 20+
- Oracle DB (dev instance)
- Redis — either via Docker or Homebrew:

```bash
# Option A — Docker (recommended)
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

### Celery (needed for live score updates and notifications)

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

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for the full step-by-step guide. Key commands:

```bash
# Build frontend
cd frontend && npm run build

# Collect static files
cd backend && python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate

# Renew SSL certificate
sudo certbot renew --nginx
```

Deploy to production by merging to `main` — GitHub Actions runs lint, tests, build, migration, and restarts services automatically.

## Features

- **Match schedule** — pick a team to win before the pick window closes; countdown timer per match
- **Powerups** — Hidden (hide your pick from others), Googly (show opponents a fake pick), The Wall (no negative points if wrong); 5 of each per season
- **Playoff auto-hide** — picks on Semi-finals, Qualifiers, and Finals are automatically hidden
- **Smart API polling** — CricAPI budget-aware; poll interval scales from 3 min (plenty of budget) to 30 min (low budget); circuit breaker at ≤3 remaining calls
- **Leaderboard** — standings table with W/L/skip counts + rank and points progression charts across all matches
- **Leaderboard snapshots** — leaderboard state saved to DB after every match result; Redis-cached for fast serving
- **In-app notifications** — rank-change alerts when #1 changes; missing-pick badge on bell icon
- **Results** — completed matches with all user picks and outcomes visible
- **Admin tools** — pause CricAPI, backfill snapshots, API quota counter, send notifications to all users
- **Rules** — full scoring, powerup, and tiebreaker rules; pick window dynamically reflects admin setting

## Testing

```bash
cd backend
pytest apps/picks/tests.py apps/leaderboard/tests.py apps/notifications/tests.py -v
```

Test settings use SQLite in-memory (`config.settings.test`) — no Oracle needed.

## Status

Live in production. All core features shipped:
- Pick placement with powerups and playoff auto-hide
- Scoring engine with skip/disqualification logic
- Leaderboard with DB-backed history snapshots and progression charts
- In-app notifications for rank changes
- CricAPI live score polling with budget management
- Google OAuth login
- PWA-ready (installable on mobile)
