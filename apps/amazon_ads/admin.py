from django.contrib import admin
from .models import (
    Campaign, AdGroup, Keyword, SearchTerm,
    NegativeKeyword, CampaignPerformance, KeywordPerformance
)


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ['name', 'account', 'campaign_type', 'state', 'daily_budget', 'created_at']
    list_filter = ['campaign_type', 'state', 'created_at']
    search_fields = ['name', 'campaign_id', 'account__account_name']
    readonly_fields = ['created_at', 'updated_at', 'last_synced_at']


@admin.register(AdGroup)
class AdGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'campaign', 'state', 'default_bid', 'created_at']
    list_filter = ['state', 'created_at']
    search_fields = ['name', 'ad_group_id', 'campaign__name']


@admin.register(Keyword)
class KeywordAdmin(admin.ModelAdmin):
    list_display = ['keyword_text', 'ad_group', 'match_type', 'state', 'bid', 'created_at']
    list_filter = ['match_type', 'state', 'created_at']
    search_fields = ['keyword_text', 'keyword_id']


@admin.register(SearchTerm)
class SearchTermAdmin(admin.ModelAdmin):
    list_display = ['query', 'campaign', 'date', 'impressions', 'clicks', 'cost', 'sales']
    list_filter = ['date', 'campaign']
    search_fields = ['query']
    date_hierarchy = 'date'


@admin.register(NegativeKeyword)
class NegativeKeywordAdmin(admin.ModelAdmin):
    list_display = ['keyword_text', 'match_type', 'campaign', 'ad_group', 'state']
    list_filter = ['match_type', 'state']
    search_fields = ['keyword_text']


@admin.register(CampaignPerformance)
class CampaignPerformanceAdmin(admin.ModelAdmin):
    list_display = ['campaign', 'date', 'impressions', 'clicks', 'cost', 'sales', 'acos']
    list_filter = ['date']
    date_hierarchy = 'date'


@admin.register(KeywordPerformance)
class KeywordPerformanceAdmin(admin.ModelAdmin):
    list_display = ['keyword', 'date', 'impressions', 'clicks', 'cost', 'sales', 'acos']
    list_filter = ['date']
    date_hierarchy = 'date'

