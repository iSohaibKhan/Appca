"""
Service for monitoring inventory and managing auto pause/resume.
"""
from django.utils import timezone
from apps.amazon_sp.models import Inventory as SPInventory
from apps.inventory.models import InventoryAlert, AutoPauseRule
from apps.amazon_ads.models import Campaign


class InventoryMonitoringService:
    """
    Service for monitoring inventory levels and triggering alerts/actions.
    
    TODO: Phase 4 - Implement inventory monitoring
    TODO: Phase 4 - Implement auto pause/resume logic
    """
    
    @staticmethod
    def check_inventory_levels(account):
        """
        Check inventory levels and create alerts if needed.
        
        TODO: Phase 4 - Implement inventory checking
        """
        today = timezone.now().date()
        
        # Get latest inventory for account's products
        products = account.products.all()
        
        for product in products:
            inventory = SPInventory.objects.filter(
                product=product,
                date=today
            ).first()
            
            if not inventory:
                continue
            
            total_available = inventory.calculate_total_available()
            
            # Check for low stock
            if total_available <= inventory.low_stock_threshold:
                # Create or update alert
                alert, created = InventoryAlert.objects.get_or_create(
                    account=account,
                    product=product,
                    status='active',
                    defaults={
                        'alert_type': 'low_stock' if total_available > 0 else 'out_of_stock',
                        'current_stock': total_available,
                        'threshold': inventory.low_stock_threshold,
                        'message': f"Stock level ({total_available}) is below threshold ({inventory.low_stock_threshold})"
                    }
                )
                
                # Check auto-pause rules
                InventoryMonitoringService._check_auto_pause_rules(account, product, total_available)
    
    @staticmethod
    def _check_auto_pause_rules(account, product, current_stock):
        """
        Check and execute auto-pause rules.
        
        TODO: Phase 4 - Implement auto-pause logic
        """
        rules = AutoPauseRule.objects.filter(
            account=account,
            is_active=True
        )
        
        for rule in rules:
            # Check if product is in scope
            if not rule.applies_to_all_products and product not in rule.products.all():
                continue
            
            # Check if stock is below threshold
            if current_stock <= rule.stock_threshold:
                # Pause campaigns
                campaigns = rule.campaigns.all() if not rule.applies_to_all_campaigns else Campaign.objects.filter(account=account)
                
                for campaign in campaigns:
                    if campaign.state == 'enabled':
                        # TODO: Phase 4 - Pause campaign via API
                        campaign.state = 'paused'
                        campaign.save()
    
    @staticmethod
    def check_restock(account):
        """
        Check for restocked products and resume campaigns if needed.
        
        TODO: Phase 4 - Implement restock checking
        """
        rules = AutoPauseRule.objects.filter(
            account=account,
            is_active=True,
            auto_resume=True
        )
        
        for rule in rules:
            products = rule.products.all() if not rule.applies_to_all_products else account.products.all()
            
            for product in products:
                today = timezone.now().date()
                inventory = SPInventory.objects.filter(
                    product=product,
                    date=today
                ).first()
                
                if inventory and inventory.calculate_total_available() >= rule.resume_threshold:
                    # Resume campaigns
                    campaigns = rule.campaigns.all() if not rule.applies_to_all_campaigns else Campaign.objects.filter(account=account)
                    
                    for campaign in campaigns:
                        if campaign.state == 'paused':
                            # TODO: Phase 4 - Resume campaign via API
                            campaign.state = 'enabled'
                            campaign.save()

