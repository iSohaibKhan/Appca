"""
Audit logs for tracking all automated changes.
"""
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class AuditLog(models.Model):
    """
    Audit log entry for tracking automated changes.
    """
    ACTION_CHOICES = [
        ('keyword_bid_update', 'Keyword Bid Update'),
        ('keyword_pause', 'Keyword Pause'),
        ('keyword_enable', 'Keyword Enable'),
        ('campaign_budget_update', 'Campaign Budget Update'),
        ('campaign_pause', 'Campaign Pause'),
        ('campaign_enable', 'Campaign Enable'),
        ('negative_keyword_add', 'Add Negative Keyword'),
        ('negative_keyword_remove', 'Remove Negative Keyword'),
    ]
    
    account = models.ForeignKey(
        'amazon_auth.AmazonAccount',
        on_delete=models.CASCADE,
        related_name='audit_logs'
    )
    
    # Action details
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    entity_type = models.CharField(max_length=50, help_text="e.g., 'keyword', 'campaign'")
    entity_id = models.CharField(max_length=100, help_text="ID of the entity")
    
    # Change details
    old_value = models.CharField(max_length=255, blank=True, help_text="Value before change")
    new_value = models.CharField(max_length=255, blank=True, help_text="Value after change")
    
    # Context
    reason = models.TextField(help_text="Explanation of why the change was made")
    rule_id = models.IntegerField(null=True, blank=True, help_text="ID of automation rule if applicable")
    execution_id = models.IntegerField(null=True, blank=True, help_text="ID of autopilot execution if applicable")
    
    # User who triggered (if manual) or system
    triggered_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    is_automated = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'audit_logs_audit_log'
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['account', 'created_at']),
            models.Index(fields=['action', 'created_at']),
            models.Index(fields=['entity_type', 'entity_id']),
        ]
    
    def __str__(self):
        return f"{self.action} - {self.entity_type}:{self.entity_id} - {self.created_at}"

