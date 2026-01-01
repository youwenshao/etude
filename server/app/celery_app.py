"""Celery application configuration."""

import os
from celery import Celery

from app.config import settings

# Create Celery app
celery_app = Celery(
    "etude",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.fingering_tasks", "app.tasks.rendering_tasks"],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)

# Task routing
celery_app.conf.task_routes = {
    "app.tasks.fingering_tasks.*": {"queue": "fingering"},
    "app.tasks.omr_tasks.*": {"queue": "omr"},
    "app.tasks.rendering_tasks.*": {"queue": "rendering"},
}

