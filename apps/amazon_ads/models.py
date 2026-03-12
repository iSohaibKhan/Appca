"""
Amazon Advertising API models.
Campaigns, Ad Groups, Keywords, Search Terms, etc.
"""
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class Campaign(models.Model):
    """
    Amazon Sponsored Products Campaign.
    """
    CAMPAIGN_TYPE_CHOICES = [
        ('sponsored_products', 'Sponsored Products'),
        ('sponsored_brands', 'Sponsored Brands'),
        ('sponsored_display', 'Sponsored Display'),
    ]
    
    STATE_CHOICES = [
        ('enabled', 'Enabled'),
        ('paused', 'Paused'),
        ('archived', 'Archived'),
    ]
    
    BIDDING_STRATEGY_CHOICES = [
        ('legacy_for_sales', 'Legacy for Sales'),
        ('auto_for_sales', 'Auto for Sales'),
        ('manual', 'Manual'),
    ]
    
    # Foreign keys
    account = models.ForeignKey(
        'amazon_auth.AmazonAccount',
        on_delete=models.CASCADE,
        related_name='campaigns'
    )
    
    # Amazon identifiers
    campaign_id = models.CharField(max_length=100, unique=True, db_index=True)
    portfolio_id = models.CharField(max_length=100, blank=True)
    
    # Campaign details
    name = models.CharField(max_length=255)
    campaign_type = models.CharField(max_length=50, choices=CAMPAIGN_TYPE_CHOICES, default='sponsored_products')
    state = models.CharField(max_length=20, choices=STATE_CHOICES, default='enabled')
    
    # Budget
    daily_budget = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    # Bidding
    bidding_strategy = models.CharField(max_length=50, choices=BIDDING_STRATEGY_CHOICES, default='manual')
    
    # Targeting
    targeting_type = models.CharField(max_length=50, blank=True)
    
    # Timestamps
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'amazon_ads_campaign'
        verbose_name = 'Campaign'
        verbose_name_plural = 'Campaigns'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['account', 'state']),
            models.Index(fields=['campaign_id']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.campaign_id})"


class AdGroup(models.Model):
    """
    Ad Group within a Campaign.
    """
    STATE_CHOICES = [
        ('enabled', 'Enabled'),
        ('paused', 'Paused'),
        ('archived', 'Archived'),
    ]
    
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name='ad_groups'
    )
    
    # Amazon identifiers
    ad_group_id = models.CharField(max_length=100, unique=True, db_index=True)
    
    # Ad Group details
    name = models.CharField(max_length=255)
    state = models.CharField(max_length=20, choices=STATE_CHOICES, default='enabled')
    default_bid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'amazon_ads_ad_group'
        verbose_name = 'Ad Group'
        verbose_name_plural = 'Ad Groups'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['campaign', 'state']),
            models.Index(fields=['ad_group_id']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.ad_group_id})"


class Keyword(models.Model):
    """
    Keyword within an Ad Group.
    """
    MATCH_TYPE_CHOICES = [
        ('exact', 'Exact'),
        ('phrase', 'Phrase'),
        ('broad', 'Broad'),
        ('negativeExact', 'Negative Exact'),
        ('negativePhrase', 'Negative Phrase'),
    ]
    
    STATE_CHOICES = [
        ('enabled', 'Enabled'),
        ('paused', 'Paused'),
        ('archived', 'Archived'),
    ]
    
    ad_group = models.ForeignKey(
        AdGroup,
        on_delete=models.CASCADE,
        related_name='keywords'
    )
    
    # Amazon identifiers
    keyword_id = models.CharField(max_length=100, unique=True, db_index=True)
    
    # Keyword details
    keyword_text = models.CharField(max_length=255)
    match_type = models.CharField(max_length=20, choices=MATCH_TYPE_CHOICES)
    state = models.CharField(max_length=20, choices=STATE_CHOICES, default='enabled')
    bid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'amazon_ads_keyword'
        verbose_name = 'Keyword'
        verbose_name_plural = 'Keywords'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['ad_group', 'state']),
            models.Index(fields=['keyword_id']),
            models.Index(fields=['keyword_text']),
        ]
    
    def __str__(self):
        return f"{self.keyword_text} ({self.match_type})"


class SearchTerm(models.Model):
    """
    Search Terms report data - actual search queries that triggered ads.
    """
    keyword = models.ForeignKey(
        Keyword,
        on_delete=models.CASCADE,
        related_name='search_terms',
        null=True,
        blank=True
    )
    ad_group = models.ForeignKey(
        AdGroup,
        on_delete=models.CASCADE,
        related_name='search_terms'
    )
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name='search_terms'
    )
    
    # Search term details
    query = models.CharField(max_length=500, db_index=True)
    match_type = models.CharField(max_length=20, blank=True)
    
    # Performance metrics (from reports)
    impressions = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    sales = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    orders = models.IntegerField(default=0)
    acos = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    roas = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    
    # Date range for this data
    date = models.DateField(db_index=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'amazon_ads_search_term'
        verbose_name = 'Search Term'
        verbose_name_plural = 'Search Terms'
        ordering = ['-date', '-cost']
        unique_together = ['query', 'campaign', 'ad_group', 'date']
        indexes = [
            models.Index(fields=['date', 'campaign']),
            models.Index(fields=['query']),
        ]
    
    def __str__(self):
        return f"{self.query} - {self.date}"


class NegativeKeyword(models.Model):
    """
    Negative keywords to exclude from targeting.
    """
    MATCH_TYPE_CHOICES = [
        ('negativeExact', 'Negative Exact'),
        ('negativePhrase', 'Negative Phrase'),
    ]
    
    STATE_CHOICES = [
        ('enabled', 'Enabled'),
        ('paused', 'Paused'),
        ('deleted', 'Deleted'),
    ]
    
    # Can be at campaign or ad group level
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name='negative_keywords',
        null=True,
        blank=True
    )
    ad_group = models.ForeignKey(
        AdGroup,
        on_delete=models.CASCADE,
        related_name='negative_keywords',
        null=True,
        blank=True
    )
    
    # Amazon identifiers
    keyword_id = models.CharField(max_length=100, unique=True, db_index=True)
    
    # Keyword details
    keyword_text = models.CharField(max_length=255)
    match_type = models.CharField(max_length=20, choices=MATCH_TYPE_CHOICES)
    state = models.CharField(max_length=20, choices=STATE_CHOICES, default='enabled')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'amazon_ads_negative_keyword'
        verbose_name = 'Negative Keyword'
        verbose_name_plural = 'Negative Keywords'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.keyword_text} ({self.match_type})"


class CampaignPerformance(models.Model):
    """
    Aggregated campaign performance metrics.
    Updated from reports ingestion.
    """
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name='performance_data'
    )
    
    # Date range
    date = models.DateField(db_index=True)
    
    # Performance metrics
    impressions = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    sales = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    orders = models.IntegerField(default=0)
    units_sold = models.IntegerField(default=0)
    
    # Calculated metrics
    ctr = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)  # Click-through rate
    cpc = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)  # Cost per click
    acos = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)  # Advertising Cost of Sales
    roas = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)  # Return on Ad Spend
    cvr = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)  # Conversion rate
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'amazon_ads_campaign_performance'
        verbose_name = 'Campaign Performance'
        verbose_name_plural = 'Campaign Performance'
        unique_together = ['campaign', 'date']
        ordering = ['-date']
        indexes = [
            models.Index(fields=['date', 'campaign']),
        ]
    
    def __str__(self):
        return f"{self.campaign.name} - {self.date}"


class KeywordPerformance(models.Model):
    """
    Aggregated keyword performance metrics.
    """
    keyword = models.ForeignKey(
        Keyword,
        on_delete=models.CASCADE,
        related_name='performance_data'
    )
    
    # Date range
    date = models.DateField(db_index=True)
    
    # Performance metrics
    impressions = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    sales = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    orders = models.IntegerField(default=0)
    
    # Calculated metrics
    ctr = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    cpc = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    acos = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    roas = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'amazon_ads_keyword_performance'
        verbose_name = 'Keyword Performance'
        verbose_name_plural = 'Keyword Performance'
        unique_together = ['keyword', 'date']
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.keyword.keyword_text} - {self.date}"

