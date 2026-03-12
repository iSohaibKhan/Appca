"""
Serializers for amazon_ads app.
"""
from rest_framework import serializers
from .models import (
    Campaign, AdGroup, Keyword, SearchTerm,
    NegativeKeyword, CampaignPerformance, KeywordPerformance
)


class CampaignSerializer(serializers.ModelSerializer):
    """Serializer for Campaign."""
    account_name = serializers.CharField(source='account.account_name', read_only=True)
    
    class Meta:
        model = Campaign
        fields = [
            'id', 'account', 'account_name', 'campaign_id', 'portfolio_id',
            'name', 'campaign_type', 'state', 'daily_budget',
            'bidding_strategy', 'targeting_type', 'start_date', 'end_date',
            'created_at', 'updated_at', 'last_synced_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_synced_at']


class AdGroupSerializer(serializers.ModelSerializer):
    """Serializer for AdGroup."""
    campaign_name = serializers.CharField(source='campaign.name', read_only=True)
    
    class Meta:
        model = AdGroup
        fields = [
            'id', 'campaign', 'campaign_name', 'ad_group_id',
            'name', 'state', 'default_bid',
            'created_at', 'updated_at', 'last_synced_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_synced_at']


class KeywordSerializer(serializers.ModelSerializer):
    """Serializer for Keyword."""
    ad_group_name = serializers.CharField(source='ad_group.name', read_only=True)
    campaign_name = serializers.CharField(source='ad_group.campaign.name', read_only=True)
    
    class Meta:
        model = Keyword
        fields = [
            'id', 'ad_group', 'ad_group_name', 'campaign_name',
            'keyword_id', 'keyword_text', 'match_type', 'state', 'bid',
            'created_at', 'updated_at', 'last_synced_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_synced_at']


class SearchTermSerializer(serializers.ModelSerializer):
    """Serializer for SearchTerm."""
    campaign_name = serializers.CharField(source='campaign.name', read_only=True)
    ad_group_name = serializers.CharField(source='ad_group.name', read_only=True)
    
    class Meta:
        model = SearchTerm
        fields = [
            'id', 'keyword', 'ad_group', 'ad_group_name', 'campaign', 'campaign_name',
            'query', 'match_type', 'impressions', 'clicks', 'cost', 'sales',
            'orders', 'acos', 'roas', 'date', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CampaignPerformanceSerializer(serializers.ModelSerializer):
    """Serializer for CampaignPerformance."""
    campaign_name = serializers.CharField(source='campaign.name', read_only=True)
    
    class Meta:
        model = CampaignPerformance
        fields = [
            'id', 'campaign', 'campaign_name', 'date',
            'impressions', 'clicks', 'cost', 'sales', 'orders', 'units_sold',
            'ctr', 'cpc', 'acos', 'roas', 'cvr',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class KeywordPerformanceSerializer(serializers.ModelSerializer):
    """Serializer for KeywordPerformance."""
    keyword_text = serializers.CharField(source='keyword.keyword_text', read_only=True)
    
    class Meta:
        model = KeywordPerformance
        fields = [
            'id', 'keyword', 'keyword_text', 'date',
            'impressions', 'clicks', 'cost', 'sales', 'orders',
            'ctr', 'cpc', 'acos', 'roas',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

