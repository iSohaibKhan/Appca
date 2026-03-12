"""
Inventory management models for stock monitoring and auto pause/resume.
"""
from django.db import models
from django.utils import timezone


class InventoryAlert(models.Model):
    """
    Alert for low inventory situations.
    """
    ALERT_TYPE_CHOICES = [
        ('low_stock', 'Low Stock'),
        ('out_of_stock', 'Out of Stock'),
        ('restocked', 'Restocked'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
    ]
    
    account = models.ForeignKey(
        'amazon_auth.AmazonAccount',
        on_delete=models.CASCADE,
        related_name='inventory_alerts'
    )
    product = models.ForeignKey(
        'amazon_sp.Product',
        on_delete=models.CASCADE,
        related_name='inventory_alerts'
    )
    
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Alert details
    current_stock = models.IntegerField()
    threshold = models.IntegerField()
    message = models.TextField(blank=True)
    
    # Actions taken
    campaigns_paused = models.ManyToManyField(
        'amazon_ads.Campaign',
        blank=True,
        related_name='inventory_pause_alerts'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'inventory_alert'
        verbose_name = 'Inventory Alert'
        verbose_name_plural = 'Inventory Alerts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['account', 'status']),
        ]
    
    def __str__(self):
        return f"{self.product.asin} - {self.alert_type}"


class AutoPauseRule(models.Model):
    """
    Rule for automatically pausing campaigns when inventory is low.
    """
    account = models.ForeignKey(
        'amazon_auth.AmazonAccount',
        on_delete=models.CASCADE,
        related_name='auto_pause_rules'
    )
    
    # Rule configuration
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    
    # Products to monitor
    products = models.ManyToManyField(
        'amazon_sp.Product',
        related_name='auto_pause_rules'
    )
    applies_to_all_products = models.BooleanField(default=False)
    
    # Campaigns to pause
    campaigns = models.ManyToManyField(
        'amazon_ads.Campaign',
        related_name='auto_pause_rules'
    )
    applies_to_all_campaigns = models.BooleanField(default=True)
    
    # Threshold
    stock_threshold = models.IntegerField(default=10, help_text="Pause when stock falls below this")
    
    # Auto-resume
    auto_resume = models.BooleanField(default=True, help_text="Resume when stock is restored")
    resume_threshold = models.IntegerField(default=20, help_text="Resume when stock reaches this")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'inventory_auto_pause_rule'
        verbose_name = 'Auto Pause Rule'
        verbose_name_plural = 'Auto Pause Rules'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.account.account_name})"

