import uuid
from typing import Optional

from fastapi import APIRouter, Response, status
from sqlalchemy import text
from sqlmodel import Session

from app.core.deps import SessionDep
from app.db.session import engine
from app.workers.celery_app import celery_app

router = APIRouter(tags=["health"])


@router.get("/health")
def liveness() -> dict:
    return {"status": "ok"}


@router.get("/ready")
def readiness(response: Response, session: SessionDep) -> dict:
    checks: dict[str, str] = {}

    try:
        session.exec(text("SELECT 1")).one()
        checks["db"] = "ok"
    except Exception as exc:
        checks["db"] = f"fail: {type(exc).__name__}"

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        checks.setdefault("db", f"fail: {type(exc).__name__}")

    try:
        conn = celery_app.connection()
        conn.ensure_connection(max_retries=1, timeout=2)
        conn.release()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"fail: {type(exc).__name__}"

    healthy = all(v == "ok" for v in checks.values())
    if not healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ok" if healthy else "degraded", "checks": checks}
