# CTF Portal

A self-hosted platform for running Capture The Flag (CTF) competitions — challenges, teams, dynamic scoring, a live leaderboard, and an admin console, packaged behind Nginx with TLS in a single container.

## Features

- **Challenge management** — create challenges with dynamic (decaying) point values, hints with point penalties, file attachments, and optional multi-part/nested challenges
- **Flexible availability windows** — auto open/close challenges on a schedule, or manually force a challenge open/closed
- **Team play** — users belong to teams; team score, member count, and submissions are tracked together
- **Scoring & anti-abuse** — wrong-attempt tracking, per-team bans, rate limiting, and an activity log for every submission and hint reveal
- **Live leaderboard** — global team rankings with historical score charts (Chart.js)
- **Admin console** — manage users/teams/challenges, bulk-import users via CSV/Excel, view submission history, set a global competition timer, and watch a live traffic/WebSocket stream of activity
- **Security-first backend** — JWT authentication, field-level AES (Fernet) encryption for sensitive DB columns, hashed flags, and an end-to-end encryption layer for API traffic
- **IP banning** — ban/unban IPs at the Nginx layer via a dynamically generated config

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Vue 3 (`<script setup>`), Vite, Pinia, Vue Router, Chart.js, Sass |
| Backend | Flask, Flask-JWT-Extended, Flask-SQLAlchemy, Flask-Limiter, Flask-Sock (WebSockets) |
| Database | PostgreSQL |
| Cache / Rate limiting | Valkey (Redis-compatible) |
| Web server | Nginx (reverse proxy + TLS termination) |
| Packaging | Multi-stage Containerfile (Bun for the frontend build, `uv` for Python deps), Docker/Podman Compose |

## Architecture

```
┌────────────┐      ┌───────────────────────────────┐
│   Client   │◄────►│  Nginx (8080/8443, TLS)        │
└────────────┘      │   ├─ static Vue build           │
                     │   └─ reverse proxy → Flask/Gunicorn
                     └───────────────┬─────────────────┘
                                     │
                        ┌────────────┴────────────┐
                        │   Flask API (Gunicorn)   │
                        └──────┬─────────────┬─────┘
                               │             │
                        ┌──────▼─────┐ ┌─────▼──────┐
                        │ PostgreSQL │ │   Valkey   │
                        │  (data)    │ │ (cache/RL) │
                        └────────────┘ └────────────┘
```

At runtime, the container generates a self-signed TLS cert (if none is mounted) and an RSA keypair used for end-to-end encrypting API payloads, then starts Nginx and a Gunicorn-served Flask app with one worker per CPU core.

## Getting Started

### Prerequisites

- Docker (or Podman) and Docker Compose
- For local frontend/backend development without containers: [Bun](https://bun.sh/), Python 3.10+, and [uv](https://docs.astral.sh/uv/)

### Run with Docker Compose (recommended)

```bash
git clone https://github.com/Tharun-Kumar-A-01/ctf_portal.git
cd ctf_portal
cp .env.example .env   # then fill in secrets (see below)
docker compose up --build
```

The app will be available at `http://localhost` (redirects/serves TLS on `https://localhost` as well, via the self-signed cert).

### Environment variables

Set these in `.env` (see `.env.example` for the full list):

| Variable | Purpose |
|---|---|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | PostgreSQL credentials |
| `DATABASE_URL` | Full SQLAlchemy connection string |
| `CACHE_URL` | Valkey/Redis connection string used for rate limiting |
| `SECRET_KEY` / `JWT_SECRET_KEY` | Flask & JWT signing secrets — **change these in production** |
| `FERNET_KEY` | Key for field-level database encryption |
| `ADMIN_USERNAME` / `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Auto-creates the first admin account on first boot |
| `FLASK_ENV` | `development` or `production` |

### Local development (without Docker)

**Backend**

```bash
cd backend
uv sync
uv run python init_db.py     # create tables + seed admin (requires ADMIN_PASSWORD env var)
uv run python run.py
```

**Frontend**

```bash
cd frontend
bun install
bun run dev
```

The dev compose file (`dev.docker-compose.yml`) spins up just Postgres and Valkey with host-exposed ports, so you can point the locally running backend/frontend at them:

```bash
docker compose -f dev.docker-compose.yml up
```

### Running tests

```bash
# Backend
cd backend && uv run pytest

# Frontend
cd frontend && bun run test
```

## Project Structure

```
ctf_portal/
├── backend/
│   ├── app/
│   │   ├── routes/        # auth, challenges, admin, leaderboard, team, data-import
│   │   ├── utils/         # scoring, leaderboard helpers, rate limiting, traffic monitor
│   │   ├── models.py      # Team, User, Challenge, Submission, ActivityLog, ...
│   │   ├── security.py    # field-level encryption
│   │   └── e2e.py         # end-to-end request/response encryption
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── views/         # user (Challenges, Team) and admin (Users, Challenges, Traffic) pages
│   │   ├── stores/        # Pinia stores (auth, ui)
│   │   ├── api/           # API client
│   │   └── router/
│   └── tests/
├── Containerfile           # multi-stage build: Bun (frontend) → Python/Nginx (runtime)
├── docker-compose.yml       # production stack (app + db + cache)
├── dev.docker-compose.yml   # db + cache only, for local dev
├── nginx.conf
└── start.sh                 # container entrypoint: TLS cert, E2E keys, DB init, Gunicorn
```

## API Overview

All endpoints are served under `/api`.

| Area | Base path | Notes |
|---|---|---|
| Auth | `/api/auth` | Login, current-user info |
| Challenges | `/api/challenges` | List/view/submit flags, hints, attachments |
| Team | `/api/team` | Current user's team info |
| Leaderboard | `/api/leaderboard` | Global team rankings |
| Admin | `/api/admin` | Users, challenges, teams, CSV import, IP bans, live traffic (WebSocket), competition timer, activity log |
