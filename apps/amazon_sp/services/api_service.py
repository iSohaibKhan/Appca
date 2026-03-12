"""
Service for interacting with Amazon SP-API.
Handles API calls for products, orders, and inventory.
"""
import requests
from typing import Dict, List, Optional
from django.conf import settings
from apps.amazon_auth.models import AmazonSPAuth
from apps.amazon_auth.services.oauth_service import AmazonSPOAuthService


class AmazonSPAPIService:
    """
    Service for Amazon SP-API operations.
    
    TODO: Phase 1 - Implement SP-API client using official SDK
    TODO: Phase 4 - Add inventory sync
    TODO: Phase 4 - Add order sync
    """
    
    BASE_URL = "https://sellingpartnerapi-na.amazon.com"
    
    def __init__(self, account):
        """
        Initialize API service with an AmazonAccount.
        """
        self.account = account
        self.auth = account.sp_auth
        self.marketplace_id = account.marketplace_id or settings.AMAZON_SP_API_MARKETPLACE_ID
    
    def get_access_token(self):
        """
        Get valid access token, refreshing if necessary.
        """
        if not self.auth:
            raise ValueError("No SP-API auth found for this account")
        
        return AmazonSPOAuthService.get_access_token(self.auth)
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None):
        """
        Make authenticated SP-API request.
        
        TODO: Phase 1 - Implement with proper signing (AWS SigV4)
        """
        token = self.get_access_token()
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'x-amz-access-token': token,
        }
        
        url = f"{self.BASE_URL}{endpoint}"
        
        if method.upper() == 'GET':
            response = requests.get(url, headers=headers, params=data)
        elif method.upper() == 'POST':
            response = requests.post(url, headers=headers, json=data)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        return response.json()
    
    def get_inventory_summaries(self, skus: Optional[List[str]] = None):
        """
        Get inventory summaries for products.
        
        TODO: Phase 4 - Implement inventory fetching
        """
        endpoint = "/fba/inventory/v1/summaries"
        params = {
            'marketplaceIds': [self.marketplace_id],
        }
        if skus:
            params['sellerSkus'] = skus
        return self._make_request('GET', endpoint, params)
    
    def get_orders(self, created_after: Optional[str] = None, **filters):
        """
        Get orders from SP-API.
        
        TODO: Phase 4 - Implement order fetching
        """
        endpoint = "/orders/v0/orders"
        params = {
            'MarketplaceIds': [self.marketplace_id],
        }
        if created_after:
            params['CreatedAfter'] = created_after
        params.update(filters)
        return self._make_request('GET', endpoint, params)
    
    def get_products(self, asins: Optional[List[str]] = None):
        """
        Get product information.
        
        TODO: Phase 4 - Implement product fetching
        """
        endpoint = "/catalog/v0/items"
        params = {}
        if asins:
            params['identifiers'] = asins
        return self._make_request('GET', endpoint, params)

