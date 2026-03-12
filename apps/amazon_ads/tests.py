"""
Tests for amazon_ads app.
"""
from django.test import TestCase
from decimal import Decimal
from apps.amazon_auth.models import AmazonAccount
from apps.accounts.models import Organization, User
from .models import Campaign, AdGroup, Keyword


class CampaignModelTest(TestCase):
    """Test Campaign model."""
    
    def setUp(self):
        self.user = User.objects.create_user(email='test@example.com', password='test')
        self.org = Organization.objects.create(name='Test Org', slug='test', owner=self.user)
        self.account = AmazonAccount.objects.create(
            organization=self.org,
            account_name='Test Account'
        )
    
    def test_create_campaign(self):
        """Test campaign creation."""
        campaign = Campaign.objects.create(
            account=self.account,
            campaign_id='123456',
            name='Test Campaign',
            daily_budget=Decimal('10.00')
        )
        self.assertEqual(campaign.name, 'Test Campaign')
        self.assertEqual(campaign.state, 'enabled')

