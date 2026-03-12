"""
Views for Amazon SP-API data.
"""
from rest_framework import generics, viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Product, Inventory, Order
from .serializers import ProductSerializer, InventorySerializer, OrderSerializer


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Product read operations.
    """
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user_orgs = self.request.user.organizations.all()
        return Product.objects.filter(account__organization__in=user_orgs)


class InventoryListView(generics.ListAPIView):
    """
    List inventory levels with filtering.
    """
    serializer_class = InventorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user_orgs = self.request.user.organizations.all()
        queryset = Inventory.objects.filter(product__account__organization__in=user_orgs)
        
        product_id = self.request.query_params.get('product_id')
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        
        low_stock_only = self.request.query_params.get('low_stock_only')
        if low_stock_only == 'true':
            queryset = queryset.filter(is_low_stock=True)
        
        return queryset.order_by('-date')


class OrderListView(generics.ListAPIView):
    """
    List orders with filtering.
    """
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user_orgs = self.request.user.organizations.all()
        queryset = Order.objects.filter(account__organization__in=user_orgs)
        
        order_status = self.request.query_params.get('order_status')
        if order_status:
            queryset = queryset.filter(order_status=order_status)
        
        return queryset.order_by('-purchase_date')

