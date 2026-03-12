"""
Celery tasks for Amazon Advertising API operations.
"""
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Campaign, AdGroup, Keyword
from .services.api_service import AmazonAdsAPIService


@shared_task
def sync_campaigns(account_id):
    """
    Sync campaigns from Amazon API to database.
    
    TODO: Phase 1 - Implement campaign sync
    """
    from apps.amazon_auth.models import AmazonAccount
    
    try:
        account = AmazonAccount.objects.get(id=account_id)
        api_service = AmazonAdsAPIService(account)
        
        # Fetch campaigns from API
        campaigns_data = api_service.get_campaigns()
        
        # TODO: Phase 1 - Process and save campaigns
        
    except Exception as e:
        print(f"Error syncing campaigns for account {account_id}: {e}")


@shared_task
def sync_ad_groups(account_id, campaign_id=None):
    """
    Sync ad groups from Amazon API.
    
    TODO: Phase 1 - Implement ad group sync
    """
    pass


@shared_task
def sync_keywords(account_id, ad_group_id=None):
    """
    Sync keywords from Amazon API.
    
    TODO: Phase 1 - Implement keyword sync
    """
    pass


@shared_task
def ingest_daily_reports(account_id):
    """
    Ingest daily performance reports from Amazon API.
    Runs daily.
    
    TODO: Phase 2 - Implement report ingestion
    """
    pass


@shared_task
def update_keyword_bid(keyword_id, new_bid):
    """
    Update keyword bid via API and log change.
    
    TODO: Phase 3 - Implement bid updates for Autopilot
    """
    from apps.audit_logs.models import AuditLog
    
    try:
        keyword = Keyword.objects.get(id=keyword_id)
        old_bid = keyword.bid
        
        # Update via API
        account = keyword.ad_group.campaign.account
        api_service = AmazonAdsAPIService(account)
        api_service.update_keyword_bid(keyword.keyword_id, new_bid)
        
        # Update local model
        keyword.bid = new_bid
        keyword.save()
        
        # Log change
        AuditLog.objects.create(
            account=account,
            action='keyword_bid_update',
            entity_type='keyword',
            entity_id=keyword.id,
            old_value=str(old_bid),
            new_value=str(new_bid),
            reason='Autopilot automation',
        )
        
    except Exception as e:
        print(f"Error updating bid for keyword {keyword_id}: {e}")

