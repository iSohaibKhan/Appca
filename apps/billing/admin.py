from django.contrib import admin
from .models import SubscriptionPlan, Subscription, UsageRecord


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'plan_type', 'price_monthly', 'max_accounts', 'is_active']
    list_filter = ['plan_type', 'is_active']


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['organization', 'plan', 'status', 'current_period_end', 'created_at']
    list_filter = ['status', 'plan', 'created_at']
    search_fields = ['organization__name', 'stripe_subscription_id']


@admin.register(UsageRecord)
class UsageRecordAdmin(admin.ModelAdmin):
    list_display = ['subscription', 'date', 'accounts_count', 'campaigns_count', 'automation_runs']
    list_filter = ['date']
    date_hierarchy = 'date'

