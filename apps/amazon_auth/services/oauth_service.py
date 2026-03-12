"""
OAuth service for Amazon Advertising API and SP-API.
Handles token refresh and OAuth flows.
"""
import requests
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from ..models import AmazonAdsAuth, AmazonSPAuth


class AmazonAdsOAuthService:
    """
    Service for managing Amazon Advertising API OAuth.
    """
    
    @staticmethod
    def get_authorization_url(state=None):
        """
        Generate Amazon Ads OAuth authorization URL.
        
        TODO: Phase 1 - Implement OAuth flow
        """
        client_id = settings.AMAZON_ADS_CLIENT_ID
        redirect_uri = settings.AMAZON_ADS_REDIRECT_URI
        
        # Amazon Ads OAuth endpoint
        auth_url = (
            f"https://www.amazon.com/ap/oa?"
            f"client_id={client_id}&"
            f"scope=advertising::campaign_management&"
            f"response_type=code&"
            f"redirect_uri={redirect_uri}"
        )
        
        if state:
            auth_url += f"&state={state}"
        
        return auth_url
    
    @staticmethod
    def exchange_code_for_tokens(code):
        """
        Exchange authorization code for access and refresh tokens.
        
        TODO: Phase 1 - Implement token exchange
        """
        client_id = settings.AMAZON_ADS_CLIENT_ID
        client_secret = settings.AMAZON_ADS_CLIENT_SECRET
        redirect_uri = settings.AMAZON_ADS_REDIRECT_URI
        
        token_url = "https://api.amazon.com/auth/o2/token"
        
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': redirect_uri,
        }
        
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        
        return response.json()
    
    @staticmethod
    def refresh_access_token(auth_obj: AmazonAdsAuth):
        """
        Refresh an expired access token using refresh token.
        
        TODO: Phase 1 - Implement token refresh
        """
        client_id = settings.AMAZON_ADS_CLIENT_ID
        client_secret = settings.AMAZON_ADS_CLIENT_SECRET
        
        token_url = "https://api.amazon.com/auth/o2/token"
        
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': auth_obj.refresh_token,
            'client_id': client_id,
            'client_secret': client_secret,
        }
        
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        
        # Update auth object
        auth_obj.access_token = token_data['access_token']
        if 'refresh_token' in token_data:
            auth_obj.refresh_token = token_data['refresh_token']
        auth_obj.expires_at = timezone.now() + timedelta(seconds=token_data.get('expires_in', 3600))
        auth_obj.save()
        
        return auth_obj


class AmazonSPOAuthService:
    """
    Service for managing Amazon SP-API OAuth (LWA).
    """
    
    @staticmethod
    def get_access_token(auth_obj: AmazonSPAuth):
        """
        Get or refresh SP-API access token.
        
        TODO: Phase 1 - Implement LWA token management
        """
        if not auth_obj.needs_refresh():
            return auth_obj.access_token
        
        # Refresh token
        return AmazonSPOAuthService.refresh_access_token(auth_obj)
    
    @staticmethod
    def refresh_access_token(auth_obj: AmazonSPAuth):
        """
        Refresh SP-API access token using refresh token.
        
        TODO: Phase 1 - Implement LWA token refresh
        """
        client_id = auth_obj.client_id or settings.AMAZON_SP_API_CLIENT_ID
        client_secret = auth_obj.client_secret or settings.AMAZON_SP_API_CLIENT_SECRET
        refresh_token = auth_obj.refresh_token
        
        token_url = "https://api.amazon.com/auth/o2/token"
        
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': client_id,
            'client_secret': client_secret,
        }
        
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        
        # Update auth object
        auth_obj.access_token = token_data['access_token']
        auth_obj.expires_at = timezone.now() + timedelta(seconds=token_data.get('expires_in', 3600))
        auth_obj.save()
        
        return auth_obj

