"""
Tests for amazon_sp app.
"""
from django.test import TestCase
from apps.amazon_auth.models import AmazonAccount
from apps.accounts.models import Organization, User
from .models import Product, Inventory


class ProductModelTest(TestCase):
    """Test Product model."""
    
    def setUp(self):
        self.user = User.objects.create_user(email='test@example.com', password='test')
        self.org = Organization.objects.create(name='Test Org', slug='test', owner=self.user)
        self.account = AmazonAccount.objects.create(
            organization=self.org,
            account_name='Test Account'
        )
    
    def test_create_product(self):
        """Test product creation."""
        product = Product.objects.create(
            account=self.account,
            asin='B01234567',
            sku='TEST-SKU-001',
            title='Test Product'
        )
        self.assertEqual(product.asin, 'B01234567')
        self.assertEqual(product.sku, 'TEST-SKU-001')

