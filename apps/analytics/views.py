"""
Views for analytics data.
"""
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import DailySummary, KeywordTrend
from .serializers import DailySummarySerializer, KeywordTrendSerializer


class DailySummaryListView(generics.ListAPIView):
    """
    List daily summaries with filtering.
    """
    serializer_class = DailySummarySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user_orgs = self.request.user.organizations.all()
        queryset = DailySummary.objects.filter(account__organization__in=user_orgs)
        
        account_id = self.request.query_params.get('account_id')
        if account_id:
            queryset = queryset.filter(account_id=account_id)
        
        date_from = self.request.query_params.get('date_from')
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        
        date_to = self.request.query_params.get('date_to')
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        
        return queryset.order_by('-date')


class KeywordTrendListView(generics.ListAPIView):
    """
    List keyword trends.
    """
    serializer_class = KeywordTrendSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user_orgs = self.request.user.organizations.all()
        queryset = KeywordTrend.objects.filter(keyword__ad_group__campaign__account__organization__in=user_orgs)
        
        keyword_id = self.request.query_params.get('keyword_id')
        if keyword_id:
            queryset = queryset.filter(keyword_id=keyword_id)
        
        return queryset.order_by('-week_start')

