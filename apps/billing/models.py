"""
Billing models for Stripe subscriptions and usage tracking.
"""
from django.db import models
from decimal import Decimal


class SubscriptionPlan(models.Model):
    """
    Subscription plan definition.
    """
    PLAN_TYPE_CHOICES = [
        ('free', 'Free'),
        ('starter', 'Starter'),
        ('professional', 'Professional'),
        ('enterprise', 'Enterprise'),
    ]
    
    name = models.CharField(max_length=100)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPE_CHOICES, unique=True)
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2)
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Limits
    max_accounts = models.IntegerField(default=1)
    max_campaigns = models.IntegerField(null=True, blank=True, help_text="Null = unlimited")
    max_automation_rules = models.IntegerField(null=True, blank=True)
    
    # Features
    features = models.JSONField(default=dict, help_text="Feature flags as JSON")
    
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'billing_subscription_plan'
        verbose_name = 'Subscription Plan'
        verbose_name_plural = 'Subscription Plans'
    
    def __str__(self):
        return self.name


class Subscription(models.Model):
    """
    Organization subscription.
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('canceled', 'Canceled'),
        ('past_due', 'Past Due'),
        ('trialing', 'Trialing'),
    ]
    
    organization = models.OneToOneField(
        'accounts.Organization',
        on_delete=models.CASCADE,
        related_name='subscription'
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name='subscriptions'
    )
    
    # Stripe
    stripe_subscription_id = models.CharField(max_length=255, unique=True, blank=True)
    stripe_customer_id = models.CharField(max_length=255, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='trialing')
    
    # Dates
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'billing_subscription'
        verbose_name = 'Subscription'
        verbose_name_plural = 'Subscriptions'
    
    def __str__(self):
        return f"{self.organization.name} - {self.plan.name}"


class UsageRecord(models.Model):
    """
    Usage tracking for billing.
    """
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name='usage_records'
    )
    
    # Usage metrics
    date = models.DateField(db_index=True)
    accounts_count = models.IntegerField(default=0)
    campaigns_count = models.IntegerField(default=0)
    automation_runs = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'billing_usage_record'
        verbose_name = 'Usage Record'
        verbose_name_plural = 'Usage Records'
        unique_together = ['subscription', 'date']
        ordering = ['-date']


class PaymentMethod(models.Model):
    """
    Stored payment method (Stripe Phase 5).
    """
    organization = models.ForeignKey(
        'accounts.Organization',
        on_delete=models.CASCADE,
        related_name='payment_methods'
    )
    stripe_payment_method_id = models.CharField(max_length=255, unique=True, blank=True)
    type = models.CharField(max_length=20, default='card')
    last4 = models.CharField(max_length=4, blank=True)
    brand = models.CharField(max_length=20, blank=True)
    exp_month = models.IntegerField(null=True, blank=True)
    exp_year = models.IntegerField(null=True, blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'billing_payment_method'
        verbose_name = 'Payment Method'
        verbose_name_plural = 'Payment Methods'

    def __str__(self):
        return f"{self.brand or 'Card'} ****{self.last4}"


class Invoice(models.Model):
    """
    Billing invoice (Stripe Phase 5).
    """
    organization = models.ForeignKey(
        'accounts.Organization',
        on_delete=models.CASCADE,
        related_name='invoices'
    )
    stripe_invoice_id = models.CharField(max_length=255, unique=True, blank=True)
    amount_due = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='usd')
    status = models.CharField(max_length=20, default='draft')  # draft, open, paid, uncollectible, void
    invoice_pdf_url = models.URLField(max_length=500, blank=True)
    period_start = models.DateTimeField(null=True, blank=True)
    period_end = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'billing_invoice'
        verbose_name = 'Invoice'
        verbose_name_plural = 'Invoices'
        ordering = ['-created_at']

    def __str__(self):
        return f"Invoice {self.stripe_invoice_id or self.id} - {self.organization.name}"

