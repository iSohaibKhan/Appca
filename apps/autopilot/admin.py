from django.contrib import admin
from .models import AutopilotGoal, AutomationRule, AutopilotExecution, SafetyLimit


@admin.register(AutopilotGoal)
class AutopilotGoalAdmin(admin.ModelAdmin):
    list_display = ['name', 'account', 'goal_type', 'is_active', 'created_at']
    list_filter = ['goal_type', 'is_active', 'created_at']
    search_fields = ['name', 'account__account_name']
    filter_horizontal = ['campaigns']


@admin.register(AutomationRule)
class AutomationRuleAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'goal', 'rule_type', 'priority', 'is_active',
        'condition_metric', 'condition_operator', 'condition_value',
        'last_executed_at'
    ]
    list_filter = ['rule_type', 'is_active', 'condition_metric', 'created_at']
    search_fields = ['name', 'goal__name']
    readonly_fields = ['last_executed_at', 'created_at', 'updated_at']


@admin.register(AutopilotExecution)
class AutopilotExecutionAdmin(admin.ModelAdmin):
    list_display = [
        'rule', 'account', 'status', 'entity_type', 'entity_id',
        'condition_met', 'safety_check_passed', 'executed_at'
    ]
    list_filter = ['status', 'condition_met', 'safety_check_passed', 'executed_at']
    search_fields = ['rule__name', 'entity_id', 'reason']
    readonly_fields = ['executed_at']
    date_hierarchy = 'executed_at'


@admin.register(SafetyLimit)
class SafetyLimitAdmin(admin.ModelAdmin):
    list_display = [
        'account', 'is_enabled', 'max_bid_changes_per_day',
        'max_budget_changes_per_day', 'updated_at'
    ]
    list_filter = ['is_enabled']
    search_fields = ['account__account_name']

