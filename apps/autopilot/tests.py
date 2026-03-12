"""
Tests for autopilot app.
"""
from django.test import TestCase
from decimal import Decimal
from apps.amazon_auth.models import AmazonAccount
from apps.accounts.models import Organization, User
from .models import AutopilotGoal, AutomationRule, SafetyLimit


class AutopilotGoalTest(TestCase):
    """Test AutopilotGoal model."""
    
    def setUp(self):
        self.user = User.objects.create_user(email='test@example.com', password='test')
        self.org = Organization.objects.create(name='Test Org', slug='test', owner=self.user)
        self.account = AmazonAccount.objects.create(
            organization=self.org,
            account_name='Test Account'
        )
    
    def test_create_goal(self):
        """Test goal creation."""
        goal = AutopilotGoal.objects.create(
            account=self.account,
            name='Maximize Profit',
            goal_type='profit',
            target_acos=Decimal('25.00')
        )
        self.assertEqual(goal.goal_type, 'profit')
        self.assertEqual(goal.target_acos, Decimal('25.00'))

