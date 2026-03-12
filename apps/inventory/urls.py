"""
URL configuration for inventory app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InventoryAlertListView, AutoPauseRuleViewSet

router = DefaultRouter()
router.register(r'auto-pause-rules', AutoPauseRuleViewSet, basename='auto-pause-rule')

app_name = 'inventory'

urlpatterns = [
    path('', include(router.urls)),
    path('alerts/', InventoryAlertListView.as_view(), name='alert-list'),
]

