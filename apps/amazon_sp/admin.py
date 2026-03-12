from django.contrib import admin
from .models import Product, Inventory, Order, OrderItem


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['asin', 'sku', 'title', 'account', 'fulfillment_type', 'is_active', 'created_at']
    list_filter = ['fulfillment_type', 'is_active', 'created_at']
    search_fields = ['asin', 'sku', 'title']


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ['product', 'date', 'available_quantity', 'fba_available', 'is_low_stock']
    list_filter = ['date', 'is_low_stock']
    date_hierarchy = 'date'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_id', 'account', 'purchase_date', 'order_status', 'order_total']
    list_filter = ['order_status', 'fulfillment_channel', 'purchase_date']
    date_hierarchy = 'purchase_date'
    search_fields = ['order_id', 'amazon_order_id']


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'asin', 'sku', 'quantity_ordered', 'item_price']
    list_filter = ['order__purchase_date']
    search_fields = ['asin', 'sku', 'order__order_id']

