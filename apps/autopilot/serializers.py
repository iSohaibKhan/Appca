"""
Serializers for autopilot app.
"""
from rest_framework import serializers
from .models import AutopilotGoal, AutomationRule, AutopilotExecution, SafetyLimit


class AutopilotGoalSerializer(serializers.ModelSerializer):
    """Serializer for AutopilotGoal."""
    account_name = serializers.CharField(source='account.account_name', read_only=True)
    rules_count = serializers.SerializerMethodField()
    
    class Meta:
        model = AutopilotGoal
        fields = [
            'id', 'account', 'account_name', 'name', 'goal_type',
            'is_active', 'target_acos', 'target_roas',
            'applies_to_all_campaigns', 'campaigns', 'rules_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_rules_count(self, obj):
        return obj.rules.count()


class AutomationRuleSerializer(serializers.ModelSerializer):
    """Serializer for AutomationRule."""
    goal_name = serializers.CharField(source='goal.name', read_only=True)
    
    class Meta:
        model = AutomationRule
        fields = [
            'id', 'goal', 'goal_name', 'name', 'rule_type', 'priority', 'is_active',
            'condition_metric', 'condition_operator', 'condition_value', 'lookback_days',
            'action_value', 'action_percentage',
            'max_bid_change_percent', 'min_bid', 'max_bid',
            'last_executed_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'last_executed_at', 'created_at', 'updated_at']


class AutopilotExecutionSerializer(serializers.ModelSerializer):
    """Serializer for AutopilotExecution."""
    rule_name = serializers.CharField(source='rule.name', read_only=True)
    account_name = serializers.CharField(source='account.account_name', read_only=True)
    
    class Meta:
        model = AutopilotExecution
        fields = [
            'id', 'rule', 'rule_name', 'account', 'account_name',
            'status', 'entity_type', 'entity_id',
            'condition_met', 'metric_value', 'old_value', 'new_value',
            'reason', 'safety_check_passed', 'safety_reason',
            'executed_at'
        ]
        read_only_fields = ['id', 'executed_at']


class SafetyLimitSerializer(serializers.ModelSerializer):
    """Serializer for SafetyLimit."""
    account_name = serializers.CharField(source='account.account_name', read_only=True)
    
    class Meta:
        model = SafetyLimit
        fields = [
            'id', 'account', 'account_name',
            'max_bid_changes_per_day', 'max_budget_changes_per_day',
            'max_campaign_pauses_per_day',
            'max_daily_budget_increase_percent', 'max_daily_budget_decrease_percent',
            'is_enabled', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

