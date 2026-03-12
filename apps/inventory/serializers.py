"""
Serializers for inventory app.
"""
from rest_framework import serializers
from .models import InventoryAlert, AutoPauseRule


class InventoryAlertSerializer(serializers.ModelSerializer):
    """Serializer for InventoryAlert."""
    product_asin = serializers.CharField(source='product.asin', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    account_name = serializers.CharField(source='account.account_name', read_only=True)
    
    class Meta:
        model = InventoryAlert
        fields = [
            'id', 'account', 'account_name', 'product', 'product_asin', 'product_sku',
            'alert_type', 'status', 'current_stock', 'threshold', 'message',
            'campaigns_paused', 'created_at', 'resolved_at'
        ]
        read_only_fields = ['id', 'created_at', 'resolved_at']


class AutoPauseRuleSerializer(serializers.ModelSerializer):
    """Serializer for AutoPauseRule."""
    account_name = serializers.CharField(source='account.account_name', read_only=True)
    
    class Meta:
        model = AutoPauseRule
        fields = [
            'id', 'account', 'account_name', 'name', 'is_active',
            'products', 'applies_to_all_products',
            'campaigns', 'applies_to_all_campaigns',
            'stock_threshold', 'auto_resume', 'resume_threshold',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

