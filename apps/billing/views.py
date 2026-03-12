"""
Views for billing (Phase 5).
"""
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import SubscriptionPlan, Subscription
from .serializers import SubscriptionPlanSerializer, SubscriptionSerializer


class SubscriptionPlanListView(generics.ListAPIView):
    """
    List available subscription plans.
    """
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [IsAuthenticated]
    queryset = SubscriptionPlan.objects.filter(is_active=True)


class SubscriptionView(generics.RetrieveUpdateAPIView):
    """
    Get or update organization subscription.
    """
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Subscription.objects.filter(organization__in=self.request.user.organizations.all())

