"""
Celery tasks for inventory monitoring.
"""
from celery import shared_task
from .services.monitoring_service import InventoryMonitoringService


@shared_task
def check_inventory_levels_daily():
    """
    Check inventory levels for all accounts.
    Runs daily.
    
    TODO: Phase 4 - Set up Celery Beat schedule
    """
    from apps.amazon_auth.models import AmazonAccount
    
    accounts = AmazonAccount.objects.filter(is_active=True, is_connected=True)
    
    for account in accounts:
        try:
            InventoryMonitoringService.check_inventory_levels(account)
            InventoryMonitoringService.check_restock(account)
        except Exception as e:
            print(f"Error checking inventory for account {account.id}: {e}")

