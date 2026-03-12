from django.contrib import admin
from .models import DailySummary, KeywordTrend


@admin.register(DailySummary)
class DailySummaryAdmin(admin.ModelAdmin):
    list_display = ['account', 'date', 'total_campaigns', 'total_cost', 'total_sales', 'overall_acos']
    list_filter = ['date']
    date_hierarchy = 'date'


@admin.register(KeywordTrend)
class KeywordTrendAdmin(admin.ModelAdmin):
    list_display = ['keyword', 'week_start', 'avg_cost', 'avg_sales', 'avg_acos']
    list_filter = ['week_start']
    date_hierarchy = 'week_start'

