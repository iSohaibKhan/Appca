"""
URL configuration for billing app.
"""
from django.urls import path
from .views import SubscriptionPlanListView, SubscriptionView

app_name = 'billing'

urlpatterns = [
    path('plans/', SubscriptionPlanListView.as_view(), name='plan-list'),
    path('subscription/<int:pk>/', SubscriptionView.as_view(), name='subscription'),
]

