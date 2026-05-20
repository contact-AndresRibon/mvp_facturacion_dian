from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "facturacion_dian",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

import os

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

if os.getenv("CELERY_TASK_ALWAYS_EAGER", "").lower() in ("true", "1"):
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True

celery_app.autodiscover_tasks(["app.workers"])
