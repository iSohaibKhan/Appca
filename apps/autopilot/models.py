"""
Autopilot models for automation rules, goals, and decision engine.
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal


class AutopilotGoal(models.Model):
    """
    Goal-based automation configuration.
    Defines what the autopilot should optimize for.
    """
    GOAL_TYPE_CHOICES = [
        ('profit', 'Maximize Profit'),
        ('growth', 'Maximize Growth'),
        ('rank', 'Improve Ranking'),
        ('acos', 'Target ACOS'),
        ('roas', 'Target ROAS'),
    ]
    
    account = models.ForeignKey(
        'amazon_auth.AmazonAccount',
        on_delete=models.CASCADE,
        related_name='autopilot_goals'
    )
    
    # Goal configuration
    name = models.CharField(max_length=255)
    goal_type = models.CharField(max_length=20, choices=GOAL_TYPE_CHOICES)
    is_active = models.BooleanField(default=True)
    
    # Target values
    target_acos = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
        help_text="Target ACOS percentage (0-100)"
    )
    target_roas = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Target ROAS ratio"
    )
    
    # Scope
    applies_to_all_campaigns = models.BooleanField(default=True)
    campaigns = models.ManyToManyField(
        'amazon_ads.Campaign',
        blank=True,
        related_name='autopilot_goals'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'autopilot_goal'
        verbose_name = 'Autopilot Goal'
        verbose_name_plural = 'Autopilot Goals'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.goal_type})"


class AutomationRule(models.Model):
    """
    Rule-based automation logic.
    Defines conditions and actions for autopilot.
    """
    RULE_TYPE_CHOICES = [
        ('keyword_bid', 'Keyword Bid Adjustment'),
        ('keyword_pause', 'Pause Keyword'),
        ('keyword_enable', 'Enable Keyword'),
        ('campaign_budget', 'Campaign Budget Adjustment'),
        ('campaign_pause', 'Pause Campaign'),
        ('negative_keyword', 'Add Negative Keyword'),
    ]
    
    CONDITION_OPERATOR_CHOICES = [
        ('gt', 'Greater Than'),
        ('gte', 'Greater Than or Equal'),
        ('lt', 'Less Than'),
        ('lte', 'Less Than or Equal'),
        ('eq', 'Equals'),
        ('ne', 'Not Equals'),
    ]
    
    CONDITION_METRIC_CHOICES = [
        ('spend', 'Spend'),
        ('sales', 'Sales'),
        ('acos', 'ACOS'),
        ('roas', 'ROAS'),
        ('clicks', 'Clicks'),
        ('impressions', 'Impressions'),
        ('ctr', 'CTR'),
        ('conversions', 'Conversions'),
        ('orders', 'Orders'),
    ]
    
    goal = models.ForeignKey(
        AutopilotGoal,
        on_delete=models.CASCADE,
        related_name='rules'
    )
    
    # Rule configuration
    name = models.CharField(max_length=255)
    rule_type = models.CharField(max_length=50, choices=RULE_TYPE_CHOICES)
    priority = models.IntegerField(default=0, help_text="Higher priority rules run first")
    is_active = models.BooleanField(default=True)
    
    # Conditions
    condition_metric = models.CharField(max_length=50, choices=CONDITION_METRIC_CHOICES)
    condition_operator = models.CharField(max_length=10, choices=CONDITION_OPERATOR_CHOICES)
    condition_value = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        help_text="Threshold value for condition"
    )
    lookback_days = models.IntegerField(
        default=7,
        validators=[MinValueValidator(1), MaxValueValidator(90)],
        help_text="Number of days to look back for metrics"
    )
    
    # Actions
    action_value = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Action value (e.g., new bid amount, budget amount)"
    )
    action_percentage = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('-100')), MaxValueValidator(Decimal('100'))],
        help_text="Percentage change (e.g., -10 for 10% decrease)"
    )
    
    # Safety limits
    max_bid_change_percent = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=Decimal('20'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
        help_text="Maximum bid change percentage per day"
    )
    min_bid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Minimum bid amount"
    )
    max_bid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Maximum bid amount"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_executed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'autopilot_rule'
        verbose_name = 'Automation Rule'
        verbose_name_plural = 'Automation Rules'
        ordering = ['-priority', '-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.rule_type})"


class AutopilotExecution(models.Model):
    """
    Log of autopilot rule executions and decisions.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('executed', 'Executed'),
        ('skipped', 'Skipped'),
        ('failed', 'Failed'),
        ('blocked', 'Blocked by Safety'),
    ]
    
    rule = models.ForeignKey(
        AutomationRule,
        on_delete=models.CASCADE,
        related_name='executions'
    )
    account = models.ForeignKey(
        'amazon_auth.AmazonAccount',
        on_delete=models.CASCADE,
        related_name='autopilot_executions'
    )
    
    # Execution details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    entity_type = models.CharField(max_length=50, help_text="e.g., 'keyword', 'campaign'")
    entity_id = models.CharField(max_length=100, help_text="ID of the entity being modified")
    
    # Decision data
    condition_met = models.BooleanField(default=False)
    metric_value = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    old_value = models.CharField(max_length=255, blank=True, help_text="Value before change")
    new_value = models.CharField(max_length=255, blank=True, help_text="Value after change")
    reason = models.TextField(blank=True, help_text="Explanation of the decision")
    
    # Safety checks
    safety_check_passed = models.BooleanField(default=True)
    safety_reason = models.TextField(blank=True)
    
    # Timestamps
    executed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'autopilot_execution'
        verbose_name = 'Autopilot Execution'
        verbose_name_plural = 'Autopilot Executions'
        ordering = ['-executed_at']
        indexes = [
            models.Index(fields=['account', 'status', 'executed_at']),
            models.Index(fields=['rule', 'executed_at']),
        ]
    
    def __str__(self):
        return f"{self.rule.name} - {self.status} - {self.executed_at}"


class SafetyLimit(models.Model):
    """
    Global safety limits to prevent excessive automation.
    """
    account = models.OneToOneField(
        'amazon_auth.AmazonAccount',
        on_delete=models.CASCADE,
        related_name='safety_limits'
    )
    
    # Daily limits
    max_bid_changes_per_day = models.IntegerField(default=50, help_text="Max bid changes per day")
    max_budget_changes_per_day = models.IntegerField(default=10, help_text="Max budget changes per day")
    max_campaign_pauses_per_day = models.IntegerField(default=5, help_text="Max campaign pauses per day")
    
    # Budget limits
    max_daily_budget_increase_percent = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=Decimal('50'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))]
    )
    max_daily_budget_decrease_percent = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=Decimal('30'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))]
    )
    
    # Kill switch
    is_enabled = models.BooleanField(default=True, help_text="Master switch to disable all automation")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'autopilot_safety_limit'
        verbose_name = 'Safety Limit'
        verbose_name_plural = 'Safety Limits'
    
    def __str__(self):
        return f"Safety Limits for {self.account.account_name}"


class AutopilotPreference(models.Model):
    """
    Organization-level autopilot preferences (defaults, safety, notifications, approval, goals).
    One per organization.
    """
    organization = models.OneToOneField(
        'accounts.Organization',
        on_delete=models.CASCADE,
        related_name='autopilot_preference'
    )
    # JSON for flexible keys: default_autopilot_enabled, default_lookback_days,
    # safety limits defaults, notification_*, require_approval_*, default_goal_*
    settings = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'autopilot_preference'
        verbose_name = 'Autopilot Preference'
        verbose_name_plural = 'Autopilot Preferences'

    def __str__(self):
        return f"Autopilot preferences for {self.organization.name}"

