"""
Settings area URL sub-config. Included under path('settings/', include('config.settings_urls')).
"""
from django.urls import path
from apps.core.views import (
    settings_view,
    settings_amazon_accounts,
    settings_team,
    settings_autopilot_preferences,
    settings_notifications,
    settings_billing,
)

urlpatterns = [
    path('', settings_view, name='settings'),
    path('amazon-accounts/', settings_amazon_accounts, name='settings_amazon_accounts'),
    path('team/', settings_team, name='settings_team'),
    path('autopilot-preferences/', settings_autopilot_preferences, name='settings_autopilot_preferences'),
    path('notifications/', settings_notifications, name='settings_notifications'),
    path('billing/', settings_billing, name='settings_billing'),
]
