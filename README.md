# Maestro (tuner)

A browser tuner backed by a PyTorch note classifier, plus teacher/student accounts: a teacher assigns scales to a student by username, and the student sees them after logging in.

**Stack:** FastAPI · SQLAlchemy 2 + Alembic · Postgres · bcrypt + JWT · React (Vite)

## Prerequisites
- Python 3.14
- Node 22
- Docker (for local Postgres)

## Environment variables
| Name | Purpose |
|---|---|
| `DATABASE_URL` | Postgres URL. `postgres://` and `postgresql://` are rewritten to `postgresql+psycopg://`. |
| `JWT_SECRET` | At least 32 characters. Generate one with `python -c "import secrets; print(secrets.token_urlsafe(32))"` |

## Run locally
```bash
cp .env.example .env              # then set JWT_SECRET
docker compose up -d              # Postgres on 127.0.0.1:5432
pip install -r requirements-test.txt
alembic upgrade head
python -m app.seed                # adds the scales; safe to re-run
uvicorn app.main:app --reload     # API on :8000, Swagger at /docs
cd web && npm install && npm run dev   # UI on :5173
pytest
```

## API
| Method | Path | Who |
|---|---|---|
| POST | `/auth/signup`, `/auth/login` | anyone |
| GET | `/auth/me`, `/scales` | logged in |
| POST | `/assignments` | teacher |
| GET | `/assignments/me` | student |
| POST | `/predict` | anyone (16 kHz float32 PCM) |

## Deploy
Render builds the `Dockerfile`, which runs `alembic upgrade head` and the seed before starting uvicorn. The database is Neon Postgres: set its **direct** connection string as `DATABASE_URL` on Render. Every push to `main` deploys.

## Next
- Teacher–student linking (class join codes), so teachers only see their own students
- Due dates and completion
- Recording practice and reporting the most out-of-tune notes
- httpOnly cookie sessions, refresh tokens, login rate limiting
- Frontend tests (Vitest)
