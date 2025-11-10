from celery import Celery
from celery.schedules import crontab
from src.config import settings

# Create Celery app
celery_app = Celery(
    'unified_inbox',
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=['src.tasks.sync_tasks']
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Periodic task schedule
celery_app.conf.beat_schedule = {
    'sync-all-accounts': {
        'task': 'src.tasks.sync_tasks.sync_all_accounts',
        'schedule': crontab(minute=f'*/{settings.SYNC_INTERVAL_MINUTES}'),
    },
}
