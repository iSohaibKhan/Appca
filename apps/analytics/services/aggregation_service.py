"""
Service for aggregating analytics metrics.
"""
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from ..models import DailySummary
from apps.amazon_ads.models import CampaignPerformance, Campaign


class AggregationService:
    """
    Service for aggregating performance metrics.
    
    TODO: Phase 2 - Implement daily aggregation
    TODO: Phase 2 - Implement keyword trend analysis
    """
    
    @staticmethod
    def aggregate_daily_summary(account, date=None):
        """
        Aggregate daily metrics for an account.
        
        TODO: Phase 2 - Implement aggregation logic
        """
        if not date:
            date = timezone.now().date()
        
        # Get all campaigns for account
        campaigns = Campaign.objects.filter(account=account)
        
        # Get performance data for date
        performances = CampaignPerformance.objects.filter(
            campaign__in=campaigns,
            date=date
        )
        
        # Aggregate metrics
        total_impressions = sum(p.impressions for p in performances)
        total_clicks = sum(p.clicks for p in performances)
        total_cost = sum(p.cost for p in performances)
        total_sales = sum(p.sales for p in performances)
        total_orders = sum(p.orders for p in performances)
        total_units_sold = sum(p.units_sold for p in performances)
        
        # Calculate metrics
        overall_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else None
        overall_cpc = (total_cost / total_clicks) if total_clicks > 0 else None
        overall_acos = (total_cost / total_sales * 100) if total_sales > 0 else None
        overall_roas = (total_sales / total_cost) if total_cost > 0 else None
        overall_cvr = (total_orders / total_clicks * 100) if total_clicks > 0 else None
        
        # Create or update summary
        summary, created = DailySummary.objects.update_or_create(
            account=account,
            date=date,
            defaults={
                'total_campaigns': campaigns.count(),
                'active_campaigns': campaigns.filter(state='enabled').count(),
                'total_impressions': total_impressions,
                'total_clicks': total_clicks,
                'total_cost': total_cost,
                'total_sales': total_sales,
                'total_orders': total_orders,
                'total_units_sold': total_units_sold,
                'overall_ctr': overall_ctr,
                'overall_cpc': overall_cpc,
                'overall_acos': overall_acos,
                'overall_roas': overall_roas,
                'overall_cvr': overall_cvr,
            }
        )
        
        return summary

