"""
Serializers for billing app.
"""
from rest_framework import serializers
from .models import SubscriptionPlan, Subscription


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """Serializer for SubscriptionPlan."""
    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'name', 'plan_type', 'price_monthly', 'price_yearly',
            'max_accounts', 'max_campaigns', 'max_automation_rules',
            'features', 'is_active'
        ]


class SubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for Subscription."""
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    
    class Meta:
        model = Subscription
        fields = [
            'id', 'organization', 'organization_name', 'plan', 'plan_name',
            'stripe_subscription_id', 'status',
            'current_period_start', 'current_period_end', 'cancel_at_period_end',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

