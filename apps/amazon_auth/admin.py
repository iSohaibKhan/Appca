from django.contrib import admin
from .models import AmazonAccount, AmazonAdsAuth, AmazonSPAuth


@admin.register(AmazonAccount)
class AmazonAccountAdmin(admin.ModelAdmin):
    """Admin interface for AmazonAccount."""
    list_display = ['account_name', 'organization', 'account_type', 'is_active', 'is_connected', 'created_at']
    list_filter = ['account_type', 'is_active', 'is_connected', 'created_at']
    search_fields = ['account_name', 'organization__name', 'profile_id', 'seller_id']
    readonly_fields = ['created_at', 'updated_at', 'last_sync_at']


@admin.register(AmazonAdsAuth)
class AmazonAdsAuthAdmin(admin.ModelAdmin):
    """Admin interface for AmazonAdsAuth."""
    list_display = ['account', 'token_type', 'expires_at', 'is_token_expired', 'created_at']
    list_filter = ['token_type', 'expires_at']
    readonly_fields = ['created_at', 'updated_at']
    
    def is_token_expired(self, obj):
        return obj.is_token_expired()
    is_token_expired.boolean = True
    is_token_expired.short_description = 'Expired'


@admin.register(AmazonSPAuth)
class AmazonSPAuthAdmin(admin.ModelAdmin):
    """Admin interface for AmazonSPAuth."""
    list_display = ['account', 'token_type', 'expires_at', 'is_token_expired', 'created_at']
    list_filter = ['token_type', 'expires_at']
    readonly_fields = ['created_at', 'updated_at']
    
    def is_token_expired(self, obj):
        return obj.is_token_expired()
    is_token_expired.boolean = True
    is_token_expired.short_description = 'Expired'

