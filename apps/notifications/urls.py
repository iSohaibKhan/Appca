"""
URL configuration for notifications app.
"""
from django.urls import path
from .views import (
    NotificationListView,
    NotificationMarkReadView,
    NotificationPreferenceView,
)

app_name = 'notifications'

urlpatterns = [
    path('', NotificationListView.as_view(), name='notification-list'),
    path('<int:notification_id>/mark-read/', NotificationMarkReadView.as_view(), name='notification-mark-read'),
    path('preferences/', NotificationPreferenceView.as_view(), name='notification-preference'),
]

