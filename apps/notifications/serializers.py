"""
Serializers for notifications app.
"""
from rest_framework import serializers
from .models import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification."""
    class Meta:
        model = Notification
        fields = [
            'id', 'type', 'title', 'message',
            'entity_type', 'entity_id',
            'is_read', 'created_at', 'read_at'
        ]
        read_only_fields = ['id', 'created_at', 'read_at']


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for NotificationPreference."""
    class Meta:
        model = NotificationPreference
        fields = [
            'id', 'email_autopilot_actions', 'email_low_inventory',
            'email_spend_alerts', 'email_daily_summary',
            'in_app_autopilot_actions', 'in_app_low_inventory',
            'in_app_spend_alerts', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

