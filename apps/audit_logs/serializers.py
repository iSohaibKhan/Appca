"""
Serializers for audit_logs app.
"""
from rest_framework import serializers
from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for AuditLog."""
    account_name = serializers.CharField(source='account.account_name', read_only=True)
    triggered_by_email = serializers.CharField(source='triggered_by.email', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = [
            'id', 'account', 'account_name', 'action',
            'entity_type', 'entity_id',
            'old_value', 'new_value',
            'reason', 'rule_id', 'execution_id',
            'triggered_by', 'triggered_by_email', 'is_automated',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']

