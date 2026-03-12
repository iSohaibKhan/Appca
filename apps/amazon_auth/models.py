"""
Amazon OAuth token management models.
Handles both Amazon Advertising API and SP-API authentication.
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
from cryptography.fernet import Fernet
import base64
import hashlib


class EncryptedTextField(models.TextField):
    """
    Custom field that encrypts/decrypts data automatically.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return self.decrypt(value)
    
    def to_python(self, value):
        if isinstance(value, str) and value:
            return self.decrypt(value)
        return value
    
    def get_prep_value(self, value):
        if value is None:
            return value
        return self.encrypt(value)
    
    def encrypt(self, value):
        """Encrypt a value using Fernet."""
        if not value:
            return value
        key = self.get_encryption_key()
        if not key:
            # If no key is set, store as plain text (not recommended for production)
            return value
        f = Fernet(key)
        return f.encrypt(value.encode()).decode()
    
    def decrypt(self, value):
        """Decrypt a value using Fernet."""
        if not value:
            return value
        key = self.get_encryption_key()
        if not key:
            return value
        try:
            f = Fernet(key)
            return f.decrypt(value.encode()).decode()
        except Exception:
            # If decryption fails, return as-is (might be plain text)
            return value
    
    def get_encryption_key(self):
        """Get encryption key from settings."""
        key = getattr(settings, 'ENCRYPTION_KEY', b'')
        if not key:
            return None
        if isinstance(key, str):
            key = key.encode()
        # Ensure key is 32 bytes for Fernet
        if len(key) != 32:
            # Derive a 32-byte key from the provided key
            key = hashlib.sha256(key).digest()
        # Encode to base64 for Fernet
        return base64.urlsafe_b64encode(key)


class AmazonAccount(models.Model):
    """
    Represents a connected Amazon account (seller/advertiser).
    Links to an organization and stores authentication tokens.
    """
    ACCOUNT_TYPE_CHOICES = [
        ('advertiser', 'Advertiser (Advertising API)'),
        ('seller', 'Seller (SP-API)'),
        ('both', 'Both'),
    ]
    
    organization = models.ForeignKey(
        'accounts.Organization',
        on_delete=models.CASCADE,
        related_name='amazon_accounts'
    )
    account_name = models.CharField(max_length=255, help_text="Friendly name for this account")
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES, default='both')
    
    # Amazon account identifiers
    profile_id = models.CharField(max_length=100, blank=True, help_text="Amazon profile/advertiser ID")
    seller_id = models.CharField(max_length=100, blank=True, help_text="Amazon Seller ID")
    marketplace_id = models.CharField(max_length=100, blank=True, help_text="Marketplace ID")
    
    # Status
    is_active = models.BooleanField(default=True)
    is_connected = models.BooleanField(default=False)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'amazon_auth_account'
        verbose_name = 'Amazon Account'
        verbose_name_plural = 'Amazon Accounts'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.account_name} ({self.organization.name})"


class AmazonAdsAuth(models.Model):
    """
    Amazon Advertising API OAuth tokens.
    """
    account = models.OneToOneField(
        AmazonAccount,
        on_delete=models.CASCADE,
        related_name='ads_auth'
    )
    
    # OAuth tokens (encrypted)
    access_token = EncryptedTextField(help_text="Encrypted access token")
    refresh_token = EncryptedTextField(help_text="Encrypted refresh token")
    token_type = models.CharField(max_length=50, default='bearer')
    
    # Token metadata
    expires_at = models.DateTimeField(help_text="When the access token expires")
    scope = models.TextField(blank=True, help_text="OAuth scopes")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'amazon_auth_ads'
        verbose_name = 'Amazon Ads Auth'
        verbose_name_plural = 'Amazon Ads Auth'
    
    def __str__(self):
        return f"Ads Auth for {self.account.account_name}"
    
    def is_token_expired(self):
        """Check if access token is expired."""
        if not self.expires_at:
            return True
        return timezone.now() >= self.expires_at
    
    def needs_refresh(self):
        """Check if token needs refresh (within 5 minutes of expiry)."""
        if not self.expires_at:
            return True
        threshold = timezone.now() + timezone.timedelta(minutes=5)
        return threshold >= self.expires_at


class AmazonSPAuth(models.Model):
    """
    Amazon SP-API (LWA) authentication tokens.
    """
    account = models.OneToOneField(
        AmazonAccount,
        on_delete=models.CASCADE,
        related_name='sp_auth'
    )
    
    # LWA tokens (encrypted)
    access_token = EncryptedTextField(help_text="Encrypted access token")
    refresh_token = EncryptedTextField(help_text="Encrypted refresh token")
    token_type = models.CharField(max_length=50, default='bearer')
    
    # Token metadata
    expires_at = models.DateTimeField(help_text="When the access token expires")
    
    # SP-API specific
    client_id = models.CharField(max_length=255, blank=True)
    client_secret = EncryptedTextField(blank=True, help_text="Encrypted client secret")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'amazon_auth_sp'
        verbose_name = 'Amazon SP-API Auth'
        verbose_name_plural = 'Amazon SP-API Auth'
    
    def __str__(self):
        return f"SP-API Auth for {self.account.account_name}"
    
    def is_token_expired(self):
        """Check if access token is expired."""
        if not self.expires_at:
            return True
        return timezone.now() >= self.expires_at
    
    def needs_refresh(self):
        """Check if token needs refresh (within 5 minutes of expiry)."""
        if not self.expires_at:
            return True
        threshold = timezone.now() + timezone.timedelta(minutes=5)
        return threshold >= self.expires_at

