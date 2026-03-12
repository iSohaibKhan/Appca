"""
Serializers for analytics app.
"""
from rest_framework import serializers
from .models import DailySummary, KeywordTrend


class DailySummarySerializer(serializers.ModelSerializer):
    """Serializer for DailySummary."""
    account_name = serializers.CharField(source='account.account_name', read_only=True)
    
    class Meta:
        model = DailySummary
        fields = [
            'id', 'account', 'account_name', 'date',
            'total_campaigns', 'active_campaigns',
            'total_impressions', 'total_clicks', 'total_cost',
            'total_sales', 'total_orders', 'total_units_sold',
            'overall_ctr', 'overall_cpc', 'overall_acos',
            'overall_roas', 'overall_cvr',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class KeywordTrendSerializer(serializers.ModelSerializer):
    """Serializer for KeywordTrend."""
    keyword_text = serializers.CharField(source='keyword.keyword_text', read_only=True)
    
    class Meta:
        model = KeywordTrend
        fields = [
            'id', 'keyword', 'keyword_text', 'week_start',
            'avg_impressions', 'avg_clicks', 'avg_cost', 'avg_sales',
            'avg_acos', 'avg_roas',
            'impressions_trend', 'cost_trend', 'sales_trend', 'acos_trend',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

