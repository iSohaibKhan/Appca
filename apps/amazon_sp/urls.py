"""
URL configuration for amazon_sp app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, InventoryListView, OrderListView

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')

app_name = 'amazon_sp'

urlpatterns = [
    path('', include(router.urls)),
    path('inventory/', InventoryListView.as_view(), name='inventory-list'),
    path('orders/', OrderListView.as_view(), name='order-list'),
]

