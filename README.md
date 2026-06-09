# TushFun

A multi-sport prediction game for friends — pick match winners, apply powerups, and compete on the leaderboard. Supports **cricket (IPL)** and **soccer (FIFA World Cup)** as independent tournaments.

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
| Analytics | PostHog |
| Server | Gunicorn + Nginx |
| Monitoring | Sentry (separate Django + React projects) |
| CI/CD | GitHub Actions |

## Project Structure

```
cricFun/
├── backend/          # Django REST API
│   ├── apps/
│   │   ├── core/         # SiteSettings, shared utilities
│   │   ├── leaderboard/  # Rankings, scores, snapshots, history
│   │   ├── matches/      # Match data, CricAPI + football-data.org sync tasks
│   │   ├── notifications/ # In-app + push notifications, rank-change alerts
│   │   ├── picks/        # Pick placement, powerups, stats
│   │   └── users/        # User profiles, tournament enrollment
│   ├── config/           # Settings (base / local / production / test)
│   └── manage.py
├── frontend/         # React SPA
│   └── src/
│       ├── api/          # Axios API clients
│       ├── components/   # UI components (layout, cards, badge, spinner...)
│       ├── pages/        # Dashboard, Schedule, Results, Leaderboard, Profile, Rules, MatchDetail
│       └── store/        # Zustand auth + tournament store
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
FOOTBALL_DATA_API_KEY=...
REDIS_URL=redis://localhost:6379/0

# PostHog analytics (optional)
VITE_POSTHOG_KEY=...
VITE_POSTHOG_HOST=...

# Sentry — leave blank to disable (create two separate projects at sentry.io)
SENTRY_DSN=           # Django (Python) project DSN
VITE_SENTRY_DSN=      # React (JavaScript) project DSN — baked in at build time
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

### Multi-sport
- **Tournament switcher** — users can switch between active tournaments (e.g. IPL and FIFA WC); each tournament has its own leaderboard, picks, and scoring
- **Soccer draw picks** — group-stage soccer matches allow picking a draw as a third outcome
- **Variable base points (soccer)** — BP scales with goal difference (win) or total goals + 1 (draw); bigger wins mean higher stakes
- **TBD team handling** — knockout matches created before teams are confirmed show as TBD; picks are blocked until teams are finalised and updated by the sync task
- **football-data.org sync** — Celery Beat polls the API for live + scheduled soccer matches; auto-retries on transient SSL errors

### Picks & Scoring
- **Match schedule** — pick a team (or draw) before the pick window closes; countdown timer per match
- **Pick window** — admin-configurable via SiteSettings; dynamically shown on Rules and Schedule pages
- **Powerups** — Hidden (hide your pick), Googly (show opponents a fake pick), The Wall (no negative points if wrong); 5 of each per season; disabled for high-stakes matches
- **High-stakes matches** — QF, SF, 3rd place, and Final (soccer) + all playoffs (cricket): auto-hidden picks, powerups blocked, non-pickers assigned to the losing side as a penalty
- **Skip budget** — first 5 skips per tournament are free (0 points); from the 6th skip onwards the user is auto-assigned the losing side of that match

### Leaderboard
- **Tournament-scoped standings** — each tournament has an independent leaderboard; enrolling in one doesn't affect the other
- **Rank + points progression charts** — DB-backed snapshots saved after every match result; Redis-cached for fast serving
- **Player form streak** — last 5 pick outcomes shown per player (W / L / S / N); draw-correct picks count as W

### Notifications
- **In-app + push notifications** — rank-change alerts, pick reminders, playoff auto-loss alerts
- **Missing-pick badge** — bell icon badge shows count of upcoming matches without a pick

### Admin & Ops
- **Pause API polling** — toggle CricAPI or football-data.org polling from Django admin without a redeploy
- **Backfill snapshots** — admin action to regenerate leaderboard history
- **API quota counter** — live call count shown in admin panel
- **Send notifications** — broadcast to all users from admin
- **Tournament management** — create tournaments, enroll users, set external_id for API sync

### Platform
- **Google OAuth login**
- **PWA-ready** — installable on mobile
- **Sentry** error tracking on backend (Django) and frontend (React)
- **PostHog** analytics — pick events and user identification scoped per tournament

## Testing

```bash
cd backend
DJANGO_SETTINGS_MODULE=config.settings.test pytest apps/picks/tests.py apps/leaderboard/tests.py apps/matches/tests.py apps/notifications/tests.py -v
```

Test settings use SQLite in-memory (`config.settings.test`) — no Oracle needed.

## Status

Live in production. All core features shipped:
- Multi-sport: cricket (IPL) + soccer (FIFA WC 2026) as independent tournaments
- Pick placement with powerups, draw picks, and high-stakes/playoff rules
- Variable soccer scoring (goal-diff BP) and cricket flat PV scoring
- Tournament-scoped leaderboard with DB-backed history snapshots and progression charts
- In-app and push notifications for rank changes and pick reminders
- CricAPI + football-data.org polling with budget management and retry logic
- Google OAuth login
- PWA-ready (installable on mobile)
- Sentry monitoring on backend and frontend
- PostHog analytics with tournament-scoped events
