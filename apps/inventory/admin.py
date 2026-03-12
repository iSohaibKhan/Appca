from django.contrib import admin
from .models import InventoryAlert, AutoPauseRule


@admin.register(InventoryAlert)
class InventoryAlertAdmin(admin.ModelAdmin):
    list_display = ['product', 'account', 'alert_type', 'status', 'current_stock', 'created_at']
    list_filter = ['alert_type', 'status', 'created_at']
    search_fields = ['product__asin', 'product__sku']


@admin.register(AutoPauseRule)
class AutoPauseRuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'account', 'is_active', 'stock_threshold', 'auto_resume', 'created_at']
    list_filter = ['is_active', 'auto_resume', 'created_at']
    filter_horizontal = ['products', 'campaigns']

