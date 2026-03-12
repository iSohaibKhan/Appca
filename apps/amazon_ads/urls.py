"""
URL configuration for amazon_ads app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CampaignViewSet, AdGroupViewSet, KeywordViewSet,
    SearchTermListView, CampaignPerformanceListView,
)

router = DefaultRouter()
router.register(r'campaigns', CampaignViewSet, basename='campaign')
router.register(r'ad-groups', AdGroupViewSet, basename='ad-group')
router.register(r'keywords', KeywordViewSet, basename='keyword')

app_name = 'amazon_ads'

urlpatterns = [
    path('', include(router.urls)),
    path('search-terms/', SearchTermListView.as_view(), name='search-term-list'),
    path('campaign-performance/', CampaignPerformanceListView.as_view(), name='campaign-performance-list'),
]

