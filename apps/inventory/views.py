"""
Views for inventory management.
"""
from rest_framework import generics, viewsets
from rest_framework.permissions import IsAuthenticated
from .models import InventoryAlert, AutoPauseRule
from .serializers import InventoryAlertSerializer, AutoPauseRuleSerializer


class InventoryAlertListView(generics.ListAPIView):
    """
    List inventory alerts.
    """
    serializer_class = InventoryAlertSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user_orgs = self.request.user.organizations.all()
        queryset = InventoryAlert.objects.filter(account__organization__in=user_orgs)
        
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.order_by('-created_at')


class AutoPauseRuleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Auto Pause Rules.
    """
    serializer_class = AutoPauseRuleSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user_orgs = self.request.user.organizations.all()
        return AutoPauseRule.objects.filter(account__organization__in=user_orgs)

