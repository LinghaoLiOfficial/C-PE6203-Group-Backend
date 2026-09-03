# Scaffold FastAPI

Reusable FastAPI scaffold for new backend projects.

## Stack

- Python 3.12
- FastAPI
- SQLAlchemy 2.x
- Alembic
- PostgreSQL
- uv

## Setup

```bash
cp .env.example .env
uv sync --group dev
uv run python -m alembic upgrade head
uv run python -m uvicorn app.main:app --reload
```

## Run

- App: `http://127.0.0.1:8000`
- Docs: `http://127.0.0.1:8000/docs`

## Included

- Auth endpoints
- Health check
- Example item CRUD
- LLM client scaffolding
- Worker scaffolding

## Auth Loading Integration

The backend exposes `GET /api/v1/auth/me` for restoring the current session and returns `401` when no valid session cookie exists. Pair it with the `scaffold-react` authentication provider: while the session is being restored or a protected route is redirecting, the frontend displays a full-viewport white 50% overlay with a large animated loader and the text `加载中...`. The loader icon and text use `text-black/20`; this is a frontend presentation concern and requires no additional backend endpoint.

## Tests

```bash
uv run python -m pytest
```
