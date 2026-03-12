"""
Service for interacting with Amazon Advertising API.
Handles API calls, error handling, and data transformation.
"""
import time
import requests
from typing import Dict, List, Optional, Any
from django.conf import settings
from apps.amazon_auth.models import AmazonAdsAuth
from apps.amazon_auth.services.oauth_service import AmazonAdsOAuthService


# Retry config: retry on 429 and 5xx, exponential backoff
DEFAULT_MAX_RETRIES = 4
DEFAULT_BACKOFF_BASE_SECONDS = 1.0
# Rate limit: min seconds between requests to avoid 429 (e.g. 0.2 = 5 req/s)
DEFAULT_MIN_REQUEST_INTERVAL = 0.2


class AmazonAdsAPIService:
    """
    Service for Amazon Advertising API operations.
    
    TODO: Phase 1 - Implement API client using official Amazon Advertising API SDK
    TODO: Phase 2 - Add campaign CRUD operations
    TODO: Phase 2 - Add reports ingestion
    """
    
    BASE_URL = "https://advertising-api.amazon.com"
    
    def __init__(self, account, min_request_interval: float = DEFAULT_MIN_REQUEST_INTERVAL):
        """
        Initialize API service with an AmazonAccount.
        min_request_interval: Min seconds between requests (rate-limit); 0 to disable.
        """
        self.account = account
        self.auth = account.ads_auth
        self._min_request_interval = min_request_interval
        self._last_request_time: float = 0.0
    
    def get_access_token(self):
        """
        Get valid access token, refreshing if necessary.
        """
        if not self.auth:
            raise ValueError("No Ads auth found for this account")
        
        if self.auth.needs_refresh():
            AmazonAdsOAuthService.refresh_access_token(self.auth)
        
        return self.auth.access_token
    
    def _get_profile_id(self) -> Optional[str]:
        """Profile ID for Ads API (required for most endpoints). Set after listProfiles."""
        return (getattr(self.account, 'profile_id', None) or '').strip() or None

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_base: float = DEFAULT_BACKOFF_BASE_SECONDS,
    ) -> Any:
        """
        Make authenticated API request with profile ID header, retries and exponential backoff.
        Retries on 429 (rate limit) and 5xx (server errors).
        """
        token = self.get_access_token()
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Amazon-Advertising-API-ClientId': settings.AMAZON_ADS_CLIENT_ID,
        }
        profile_id = self._get_profile_id()
        if profile_id:
            headers['Amazon-Advertising-API-ProfileId'] = profile_id

        url = f"{self.BASE_URL}{endpoint}"
        last_exception = None
        for attempt in range(max_retries):
            # Rate-limit: wait if we're sending requests too fast
            if self._min_request_interval > 0:
                elapsed = time.monotonic() - self._last_request_time
                if elapsed < self._min_request_interval:
                    time.sleep(self._min_request_interval - elapsed)
            try:
                if method.upper() == 'GET':
                    response = requests.get(url, headers=headers, params=data, timeout=30)
                elif method.upper() == 'POST':
                    response = requests.post(url, headers=headers, json=data, timeout=30)
                elif method.upper() == 'PUT':
                    response = requests.put(url, headers=headers, json=data, timeout=30)
                elif method.upper() == 'DELETE':
                    response = requests.delete(url, headers=headers, timeout=30)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                self._last_request_time = time.monotonic()
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt < max_retries - 1:
                        sleep_secs = backoff_base * (2 ** attempt)
                        time.sleep(sleep_secs)
                        continue
                response.raise_for_status()
                return response.json()
            except requests.exceptions.HTTPError as e:
                last_exception = e
                if e.response is not None and (
                    e.response.status_code == 429 or e.response.status_code >= 500
                ) and attempt < max_retries - 1:
                    sleep_secs = backoff_base * (2 ** attempt)
                    time.sleep(sleep_secs)
                    continue
                raise
            except requests.exceptions.RequestException as e:
                last_exception = e
                if attempt < max_retries - 1:
                    sleep_secs = backoff_base * (2 ** attempt)
                    time.sleep(sleep_secs)
                    continue
                raise
        if last_exception is not None:
            raise last_exception
        raise RuntimeError("_make_request failed after retries")
    
    def get_campaigns(self, **filters):
        """
        Fetch campaigns from Amazon API.
        
        TODO: Phase 1 - Implement campaign fetching
        """
        endpoint = "/v2/sp/campaigns"
        return self._make_request('GET', endpoint, filters)
    
    def get_ad_groups(self, campaign_id: Optional[str] = None, **filters):
        """
        Fetch ad groups from Amazon API.
        
        TODO: Phase 1 - Implement ad group fetching
        """
        endpoint = "/v2/sp/adGroups"
        if campaign_id:
            filters['campaignIdFilter'] = campaign_id
        return self._make_request('GET', endpoint, filters)
    
    def get_keywords(self, ad_group_id: Optional[str] = None, **filters):
        """
        Fetch keywords from Amazon API.
        
        TODO: Phase 1 - Implement keyword fetching
        """
        endpoint = "/v2/sp/keywords"
        if ad_group_id:
            filters['adGroupIdFilter'] = ad_group_id
        return self._make_request('GET', endpoint, filters)
    
    def update_keyword_bid(self, keyword_id: str, bid: float):
        """
        Update keyword bid.
        """
        endpoint = "/v2/sp/keywords"
        data = {
            'keywordId': keyword_id,
            'bid': bid
        }
        return self._make_request('PUT', endpoint, data)

    def update_campaign_budget(self, campaign_id: str, daily_budget: float) -> Any:
        """
        Update Sponsored Products campaign daily budget.
        campaign_id: Amazon campaign ID.
        daily_budget: Daily budget amount (e.g. 10.0 for $10/day).
        """
        endpoint = "/v2/sp/campaigns"
        data = {
            'campaignId': campaign_id,
            'dailyBudget': daily_budget,
        }
        return self._make_request('PUT', endpoint, data)

    def update_ad_group_budget(self, ad_group_id: str, daily_budget: float) -> Any:
        """
        Update ad group budget if supported by the ad type.
        SP ad groups inherit campaign budget; this is a stub for SB/SD or future use.
        """
        # SP typically does not have per-ad-group budget; campaign-level only.
        # Placeholder for Sponsored Brands/Display or API changes.
        raise NotImplementedError(
            "Ad group budget update not supported for Sponsored Products; use update_campaign_budget."
        )
    
    def request_report(self, report_type: str, **params):
        """
        Request a report from Amazon API.
        
        TODO: Phase 2 - Implement report requests
        """
        endpoint = f"/v2/{report_type}/report"
        return self._make_request('POST', endpoint, params)
    
    def get_report(self, report_id: str):
        """
        Get report status and download URL.
        
        TODO: Phase 2 - Implement report retrieval
        """
        endpoint = f"/v2/reports/{report_id}"
        return self._make_request('GET', endpoint)

