"""
Celery tasks for Amazon authentication.
"""
from celery import shared_task
from django.utils import timezone
from .models import AmazonAdsAuth, AmazonSPAuth
from .services.oauth_service import AmazonAdsOAuthService, AmazonSPOAuthService


@shared_task
def refresh_amazon_ads_tokens():
    """
    Periodic task to refresh Amazon Ads tokens before they expire.
    Runs every hour.
    
    TODO: Phase 1 - Set up Celery Beat schedule
    """
    auth_objects = AmazonAdsAuth.objects.filter(
        expires_at__lte=timezone.now() + timezone.timedelta(hours=1)
    )
    
    for auth_obj in auth_objects:
        try:
            AmazonAdsOAuthService.refresh_access_token(auth_obj)
        except Exception as e:
            # Log error but don't fail the task
            print(f"Error refreshing token for {auth_obj.account}: {e}")


@shared_task
def refresh_amazon_sp_tokens():
    """
    Periodic task to refresh Amazon SP-API tokens before they expire.
    Runs every hour.
    
    TODO: Phase 1 - Set up Celery Beat schedule
    """
    auth_objects = AmazonSPAuth.objects.filter(
        expires_at__lte=timezone.now() + timezone.timedelta(hours=1)
    )
    
    for auth_obj in auth_objects:
        try:
            AmazonSPOAuthService.refresh_access_token(auth_obj)
        except Exception as e:
            # Log error but don't fail the task
            print(f"Error refreshing token for {auth_obj.account}: {e}")

