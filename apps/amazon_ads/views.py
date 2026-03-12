"""
Views for Amazon Advertising API data.
"""
from rest_framework import generics, viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from .models import Campaign, AdGroup, Keyword, SearchTerm, CampaignPerformance
from .serializers import (
    CampaignSerializer, AdGroupSerializer, KeywordSerializer,
    SearchTermSerializer, CampaignPerformanceSerializer
)


class CampaignViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Campaign CRUD operations.
    """
    serializer_class = CampaignSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user_orgs = self.request.user.organizations.all()
        return Campaign.objects.filter(account__organization__in=user_orgs)
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class AdGroupViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Ad Group operations.
    """
    serializer_class = AdGroupSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user_orgs = self.request.user.organizations.all()
        campaign_id = self.request.query_params.get('campaign_id')
        queryset = AdGroup.objects.filter(campaign__account__organization__in=user_orgs)
        if campaign_id:
            queryset = queryset.filter(campaign_id=campaign_id)
        return queryset


class KeywordViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Keyword operations.
    """
    serializer_class = KeywordSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user_orgs = self.request.user.organizations.all()
        ad_group_id = self.request.query_params.get('ad_group_id')
        queryset = Keyword.objects.filter(ad_group__campaign__account__organization__in=user_orgs)
        if ad_group_id:
            queryset = queryset.filter(ad_group_id=ad_group_id)
        return queryset


class SearchTermListView(generics.ListAPIView):
    """
    List search terms with filtering.
    """
    serializer_class = SearchTermSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user_orgs = self.request.user.organizations.all()
        queryset = SearchTerm.objects.filter(campaign__account__organization__in=user_orgs)
        
        # Filters
        campaign_id = self.request.query_params.get('campaign_id')
        if campaign_id:
            queryset = queryset.filter(campaign_id=campaign_id)
        
        date_from = self.request.query_params.get('date_from')
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        
        date_to = self.request.query_params.get('date_to')
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        
        return queryset.order_by('-date', '-cost')


class CampaignPerformanceListView(generics.ListAPIView):
    """
    List campaign performance metrics.
    """
    serializer_class = CampaignPerformanceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user_orgs = self.request.user.organizations.all()
        queryset = CampaignPerformance.objects.filter(campaign__account__organization__in=user_orgs)
        
        campaign_id = self.request.query_params.get('campaign_id')
        if campaign_id:
            queryset = queryset.filter(campaign_id=campaign_id)
        
        date_from = self.request.query_params.get('date_from')
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        
        date_to = self.request.query_params.get('date_to')
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        
        return queryset.order_by('-date')

