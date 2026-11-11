
import logging

from celery import Celery

from app.config.settings import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "realgrowth_conversation_analysis",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.conversation_analysis.tasks",
    ],
)


celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Explicit task registration
    imports=(
        "app.conversation_analysis.tasks",
    ),

    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,

    result_expires=3600,

    timezone="UTC",
    enable_utc=True,

    broker_connection_retry_on_startup=True,
)



@celery_app.task(name="app.celery_app.health_check")
def health_check():
    logger.info("Celery health check executed successfully")

    return {
        "status": "healthy",
        "service": "celery",
        "message": "Celery worker is running",
    }
