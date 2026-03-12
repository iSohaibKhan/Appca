"""
Views for Autopilot management.
"""
from rest_framework import generics, viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import AutopilotGoal, AutomationRule, AutopilotExecution, SafetyLimit
from .serializers import (
    AutopilotGoalSerializer, AutomationRuleSerializer,
    AutopilotExecutionSerializer, SafetyLimitSerializer
)
from .services.decision_engine import DecisionEngine


class AutopilotGoalViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Autopilot Goals.
    """
    serializer_class = AutopilotGoalSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user_orgs = self.request.user.organizations.all()
        return AutopilotGoal.objects.filter(account__organization__in=user_orgs)


class AutomationRuleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Automation Rules.
    """
    serializer_class = AutomationRuleSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user_orgs = self.request.user.organizations.all()
        goal_id = self.request.query_params.get('goal_id')
        queryset = AutomationRule.objects.filter(goal__account__organization__in=user_orgs)
        if goal_id:
            queryset = queryset.filter(goal_id=goal_id)
        return queryset


class AutopilotExecutionListView(generics.ListAPIView):
    """
    List autopilot executions.
    """
    serializer_class = AutopilotExecutionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user_orgs = self.request.user.organizations.all()
        queryset = AutopilotExecution.objects.filter(account__organization__in=user_orgs)
        
        account_id = self.request.query_params.get('account_id')
        if account_id:
            queryset = queryset.filter(account_id=account_id)
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-executed_at')


class SafetyLimitView(generics.RetrieveUpdateAPIView):
    """
    Get or update safety limits.
    """
    serializer_class = SafetyLimitSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user_orgs = self.request.user.organizations.all()
        return SafetyLimit.objects.filter(account__organization__in=user_orgs)


class RunAutopilotView(generics.GenericAPIView):
    """
    Manually trigger autopilot evaluation.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Run autopilot for an account.
        """
        account_id = request.data.get('account_id')
        goal_id = request.data.get('goal_id')
        
        if not account_id:
            return Response({'error': 'account_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        from apps.amazon_auth.models import AmazonAccount
        
        try:
            account = AmazonAccount.objects.get(
                id=account_id,
                organization__in=request.user.organizations.all()
            )
            
            engine = DecisionEngine(account)
            executions = engine.evaluate_rules(goal_id=goal_id)
            
            # TODO: Phase 3 - Execute the actions
            
            return Response({
                'message': f'Autopilot evaluation completed',
                'executions_created': len(executions),
                'executions': AutopilotExecutionSerializer(executions, many=True).data
            })
        except AmazonAccount.DoesNotExist:
            return Response({'error': 'Account not found'}, status=status.HTTP_404_NOT_FOUND)

