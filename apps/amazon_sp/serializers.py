"""
Serializers for amazon_sp app.
"""
from rest_framework import serializers
from .models import Product, Inventory, Order, OrderItem


class ProductSerializer(serializers.ModelSerializer):
    """Serializer for Product."""
    account_name = serializers.CharField(source='account.account_name', read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'account', 'account_name', 'asin', 'sku',
            'title', 'brand', 'fulfillment_type', 'price',
            'is_active', 'created_at', 'updated_at', 'last_synced_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_synced_at']


class InventorySerializer(serializers.ModelSerializer):
    """Serializer for Inventory."""
    product_asin = serializers.CharField(source='product.asin', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    total_available = serializers.SerializerMethodField()
    
    class Meta:
        model = Inventory
        fields = [
            'id', 'product', 'product_asin', 'product_sku',
            'available_quantity', 'reserved_quantity', 'inbound_quantity',
            'fba_available', 'fba_reserved', 'fba_inbound',
            'low_stock_threshold', 'is_low_stock', 'total_available',
            'date', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_total_available(self, obj):
        return obj.calculate_total_available()


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for OrderItem."""
    class Meta:
        model = OrderItem
        fields = [
            'id', 'order', 'product', 'asin', 'sku', 'title',
            'quantity_ordered', 'quantity_shipped',
            'item_price', 'shipping_price', 'item_tax'
        ]


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for Order."""
    account_name = serializers.CharField(source='account.account_name', read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'account', 'account_name', 'order_id', 'amazon_order_id',
            'purchase_date', 'order_status', 'fulfillment_channel',
            'order_total', 'currency', 'ship_country', 'ship_city',
            'items', 'created_at', 'updated_at', 'last_synced_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_synced_at']

