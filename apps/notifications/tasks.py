"""
Celery tasks for notifications.
"""
from celery import shared_task
from .services.notification_service import NotificationService

