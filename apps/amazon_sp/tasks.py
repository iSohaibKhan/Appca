"""
Celery tasks for Amazon SP-API operations.
"""
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .services.api_service import AmazonSPAPIService


@shared_task
def sync_inventory(account_id):
    """
    Sync inventory levels from SP-API.
    Runs daily.
    
    TODO: Phase 4 - Implement inventory sync
    """
    from apps.amazon_auth.models import AmazonAccount
    
    try:
        account = AmazonAccount.objects.get(id=account_id)
        api_service = AmazonSPAPIService(account)
        
        # Fetch inventory
        inventory_data = api_service.get_inventory_summaries()
        
        # TODO: Phase 4 - Process and save inventory
        
    except Exception as e:
        print(f"Error syncing inventory for account {account_id}: {e}")


@shared_task
def sync_orders(account_id, days_back=7):
    """
    Sync recent orders from SP-API.
    
    TODO: Phase 4 - Implement order sync
    """
    pass


@shared_task
def check_low_stock():
    """
    Check all products for low stock and update flags.
    Runs daily.
    
    TODO: Phase 4 - Implement low stock checking
    """
    from .models import Inventory
    
    inventories = Inventory.objects.filter(date=timezone.now().date())
    for inventory in inventories:
        inventory.check_low_stock()
        inventory.save()

