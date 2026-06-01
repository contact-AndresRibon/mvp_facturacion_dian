import os

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "facturacion_dian",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_max_tasks_per_child=200,
    worker_prefetch_multiplier=1,
    task_default_queue="dian",
    task_default_exchange="dian",
    task_default_exchange_type="direct",
    task_routes={
        "app.workers.tasks.submit_invoice_to_dian": {"queue": "dian"},
        "app.workers.tasks.submit_credit_note_to_dian": {"queue": "dian"},
        "app.workers.tasks.submit_debit_note_to_dian": {"queue": "dian"},
    },
    broker_connection_retry_on_startup=True,
)

if os.getenv("CELERY_TASK_ALWAYS_EAGER", "").lower() in ("true", "1"):
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True

celery_app.autodiscover_tasks(["app.workers"])
