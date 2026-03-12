"""
URL configuration for analytics app.
"""
from django.urls import path
from .views import DailySummaryListView, KeywordTrendListView

app_name = 'analytics'

urlpatterns = [
    path('daily-summaries/', DailySummaryListView.as_view(), name='daily-summary-list'),
    path('keyword-trends/', KeywordTrendListView.as_view(), name='keyword-trend-list'),
]

