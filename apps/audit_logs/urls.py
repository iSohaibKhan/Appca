"""
URL configuration for audit_logs app.
"""
from django.urls import path
from .views import AuditLogListView

app_name = 'audit_logs'

urlpatterns = [
    path('', AuditLogListView.as_view(), name='audit-log-list'),
]

