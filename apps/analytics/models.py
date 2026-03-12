"""
Analytics models for metrics aggregation and reporting.
"""
from django.db import models
from decimal import Decimal


class DailySummary(models.Model):
    """
    Daily aggregated metrics summary for an account.
    """
    account = models.ForeignKey(
        'amazon_auth.AmazonAccount',
        on_delete=models.CASCADE,
        related_name='daily_summaries'
    )
    
    date = models.DateField(db_index=True)
    
    # Campaign metrics
    total_campaigns = models.IntegerField(default=0)
    active_campaigns = models.IntegerField(default=0)
    
    # Performance metrics
    total_impressions = models.IntegerField(default=0)
    total_clicks = models.IntegerField(default=0)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_sales = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_orders = models.IntegerField(default=0)
    total_units_sold = models.IntegerField(default=0)
    
    # Calculated metrics
    overall_ctr = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    overall_cpc = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    overall_acos = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    overall_roas = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    overall_cvr = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'analytics_daily_summary'
        verbose_name = 'Daily Summary'
        verbose_name_plural = 'Daily Summaries'
        unique_together = ['account', 'date']
        ordering = ['-date']
        indexes = [
            models.Index(fields=['account', 'date']),
        ]
    
    def __str__(self):
        return f"{self.account.account_name} - {self.date}"


class KeywordTrend(models.Model):
    """
    Keyword performance trends over time.
    """
    keyword = models.ForeignKey(
        'amazon_ads.Keyword',
        on_delete=models.CASCADE,
        related_name='trends'
    )
    
    # Time period
    week_start = models.DateField(db_index=True)
    
    # Aggregated metrics
    avg_impressions = models.IntegerField(default=0)
    avg_clicks = models.IntegerField(default=0)
    avg_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    avg_sales = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    avg_acos = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    avg_roas = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    
    # Trend indicators
    impressions_trend = models.CharField(max_length=20, blank=True, help_text="up/down/stable")
    cost_trend = models.CharField(max_length=20, blank=True)
    sales_trend = models.CharField(max_length=20, blank=True)
    acos_trend = models.CharField(max_length=20, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'analytics_keyword_trend'
        verbose_name = 'Keyword Trend'
        verbose_name_plural = 'Keyword Trends'
        unique_together = ['keyword', 'week_start']
        ordering = ['-week_start']

