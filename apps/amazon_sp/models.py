"""
Amazon SP-API models for Seller Central data.
Products, Orders, Inventory, etc.
"""
from django.db import models
from decimal import Decimal


class Product(models.Model):
    """
    Amazon product (ASIN/SKU).
    """
    FULFILLMENT_CHOICES = [
        ('FBA', 'Fulfilled by Amazon'),
        ('FBM', 'Fulfilled by Merchant'),
    ]
    
    account = models.ForeignKey(
        'amazon_auth.AmazonAccount',
        on_delete=models.CASCADE,
        related_name='products'
    )
    
    # Amazon identifiers
    asin = models.CharField(max_length=10, db_index=True, help_text="Amazon Standard Identification Number")
    sku = models.CharField(max_length=255, db_index=True, help_text="Seller SKU")
    
    # Product details
    title = models.CharField(max_length=500, blank=True)
    brand = models.CharField(max_length=255, blank=True)
    fulfillment_type = models.CharField(max_length=10, choices=FULFILLMENT_CHOICES, default='FBA')
    
    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'amazon_sp_product'
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        unique_together = ['account', 'asin']
        indexes = [
            models.Index(fields=['account', 'asin']),
            models.Index(fields=['sku']),
        ]
    
    def __str__(self):
        return f"{self.title or self.asin} ({self.sku})"


class Inventory(models.Model):
    """
    Product inventory levels.
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='inventory_records'
    )
    
    # Inventory levels
    available_quantity = models.IntegerField(default=0, help_text="Available units")
    reserved_quantity = models.IntegerField(default=0, help_text="Reserved units")
    inbound_quantity = models.IntegerField(default=0, help_text="Inbound units")
    
    # FBA specific
    fba_available = models.IntegerField(default=0, help_text="FBA available units")
    fba_reserved = models.IntegerField(default=0, help_text="FBA reserved units")
    fba_inbound = models.IntegerField(default=0, help_text="FBA inbound units")
    
    # Alert thresholds
    low_stock_threshold = models.IntegerField(default=10, help_text="Alert when stock falls below this")
    is_low_stock = models.BooleanField(default=False)
    
    # Date snapshot
    date = models.DateField(db_index=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'amazon_sp_inventory'
        verbose_name = 'Inventory'
        verbose_name_plural = 'Inventory'
        unique_together = ['product', 'date']
        ordering = ['-date']
        indexes = [
            models.Index(fields=['date', 'product']),
            models.Index(fields=['is_low_stock']),
        ]
    
    def __str__(self):
        return f"{self.product.asin} - {self.date}: {self.available_quantity} units"
    
    def calculate_total_available(self):
        """Calculate total available units."""
        return self.available_quantity + self.fba_available
    
    def check_low_stock(self):
        """Check if stock is low and update flag."""
        total = self.calculate_total_available()
        self.is_low_stock = total <= self.low_stock_threshold
        return self.is_low_stock


class Order(models.Model):
    """
    Amazon order from Seller Central.
    """
    ORDER_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Unshipped', 'Unshipped'),
        ('PartiallyShipped', 'Partially Shipped'),
        ('Shipped', 'Shipped'),
        ('Canceled', 'Canceled'),
        ('Unfulfillable', 'Unfulfillable'),
    ]
    
    FULFILLMENT_CHOICES = [
        ('MFN', 'Merchant Fulfilled Network'),
        ('AFN', 'Amazon Fulfilled Network'),
    ]
    
    account = models.ForeignKey(
        'amazon_auth.AmazonAccount',
        on_delete=models.CASCADE,
        related_name='orders'
    )
    
    # Amazon identifiers
    order_id = models.CharField(max_length=50, unique=True, db_index=True)
    amazon_order_id = models.CharField(max_length=50, blank=True)
    
    # Order details
    purchase_date = models.DateTimeField()
    order_status = models.CharField(max_length=50, choices=ORDER_STATUS_CHOICES)
    fulfillment_channel = models.CharField(max_length=10, choices=FULFILLMENT_CHOICES)
    
    # Financial
    order_total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default='USD')
    
    # Shipping
    ship_country = models.CharField(max_length=2, blank=True)
    ship_city = models.CharField(max_length=255, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'amazon_sp_order'
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        ordering = ['-purchase_date']
        indexes = [
            models.Index(fields=['account', 'order_status']),
            models.Index(fields=['purchase_date']),
        ]
    
    def __str__(self):
        return f"Order {self.order_id} - {self.order_status}"


class OrderItem(models.Model):
    """
    Individual items within an order.
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order_items'
    )
    
    # Item details
    asin = models.CharField(max_length=10)
    sku = models.CharField(max_length=255)
    title = models.CharField(max_length=500, blank=True)
    quantity_ordered = models.IntegerField(default=1)
    quantity_shipped = models.IntegerField(default=0)
    
    # Financial
    item_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    shipping_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    item_tax = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    class Meta:
        db_table = 'amazon_sp_order_item'
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'
    
    def __str__(self):
        return f"{self.order.order_id} - {self.sku} x{self.quantity_ordered}"

