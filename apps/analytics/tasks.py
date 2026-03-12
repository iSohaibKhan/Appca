"""
Celery tasks for analytics aggregation.
"""
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .services.aggregation_service import AggregationService


@shared_task
def aggregate_daily_summaries():
    """
    Aggregate daily summaries for all accounts.
    Runs daily after reports are ingested.
    
    TODO: Phase 2 - Set up Celery Beat schedule
    """
    from apps.amazon_auth.models import AmazonAccount
    
    yesterday = timezone.now().date() - timedelta(days=1)
    accounts = AmazonAccount.objects.filter(is_active=True, is_connected=True)
    
    for account in accounts:
        try:
            AggregationService.aggregate_daily_summary(account, yesterday)
        except Exception as e:
            print(f"Error aggregating summary for account {account.id}: {e}")

