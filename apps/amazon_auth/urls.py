"""
URL configuration for amazon_auth app.
"""
from django.urls import path
from .views import (
    AmazonAdsOAuthInitiateView,
    AmazonAdsOAuthCallbackView,
    AmazonAccountListView,
    AmazonAccountDetailView,
)

app_name = 'amazon_auth'

urlpatterns = [
    # OAuth Flows
    path('amazon-ads/initiate/', AmazonAdsOAuthInitiateView.as_view(), name='ads-oauth-initiate'),
    path('amazon-ads/callback/', AmazonAdsOAuthCallbackView.as_view(), name='ads-oauth-callback'),
    
    # Amazon Accounts
    path('accounts/', AmazonAccountListView.as_view(), name='account-list'),
    path('accounts/<int:pk>/', AmazonAccountDetailView.as_view(), name='account-detail'),
]

