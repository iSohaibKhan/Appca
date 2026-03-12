"""
Serializers for amazon_auth app.
"""
from rest_framework import serializers
from .models import AmazonAccount, AmazonAdsAuth, AmazonSPAuth


class AmazonAccountSerializer(serializers.ModelSerializer):
    """Serializer for AmazonAccount."""
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    is_ads_connected = serializers.SerializerMethodField()
    is_sp_connected = serializers.SerializerMethodField()
    
    class Meta:
        model = AmazonAccount
        fields = [
            'id', 'account_name', 'organization', 'organization_name',
            'account_type', 'profile_id', 'seller_id', 'marketplace_id',
            'is_active', 'is_connected', 'is_ads_connected', 'is_sp_connected',
            'last_sync_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_sync_at']
    
    def get_is_ads_connected(self, obj):
        """Check if Ads auth exists."""
        return hasattr(obj, 'ads_auth') and obj.ads_auth is not None
    
    def get_is_sp_connected(self, obj):
        """Check if SP-API auth exists."""
        return hasattr(obj, 'sp_auth') and obj.sp_auth is not None


class AmazonAdsAuthSerializer(serializers.ModelSerializer):
    """Serializer for AmazonAdsAuth (read-only for security)."""
    account_name = serializers.CharField(source='account.account_name', read_only=True)
    
    class Meta:
        model = AmazonAdsAuth
        fields = [
            'id', 'account', 'account_name', 'token_type',
            'expires_at', 'scope', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AmazonSPAuthSerializer(serializers.ModelSerializer):
    """Serializer for AmazonSPAuth (read-only for security)."""
    account_name = serializers.CharField(source='account.account_name', read_only=True)
    
    class Meta:
        model = AmazonSPAuth
        fields = [
            'id', 'account', 'account_name', 'token_type',
            'expires_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

