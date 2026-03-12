"""
URL configuration for autopilot app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AutopilotGoalViewSet, AutomationRuleViewSet,
    AutopilotExecutionListView, SafetyLimitView, RunAutopilotView,
)

router = DefaultRouter()
router.register(r'goals', AutopilotGoalViewSet, basename='goal')
router.register(r'rules', AutomationRuleViewSet, basename='rule')

app_name = 'autopilot'

urlpatterns = [
    path('', include(router.urls)),
    path('executions/', AutopilotExecutionListView.as_view(), name='execution-list'),
    path('safety-limits/<int:pk>/', SafetyLimitView.as_view(), name='safety-limit'),
    path('run/', RunAutopilotView.as_view(), name='run-autopilot'),
]

