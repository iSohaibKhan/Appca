"""
Tests for amazon_auth app.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.accounts.models import Organization
from .models import AmazonAccount

User = get_user_model()


class AmazonAccountModelTest(TestCase):
    """Test AmazonAccount model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.org = Organization.objects.create(
            name='Test Org',
            slug='test-org',
            owner=self.user
        )
    
    def test_create_amazon_account(self):
        """Test Amazon account creation."""
        account = AmazonAccount.objects.create(
            organization=self.org,
            account_name='Test Account',
            account_type='both'
        )
        self.assertEqual(account.account_name, 'Test Account')
        self.assertEqual(account.organization, self.org)
        self.assertFalse(account.is_connected)

