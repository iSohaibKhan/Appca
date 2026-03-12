"""
Core views for dashboard and main pages.
"""
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout, get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q
from django.core.paginator import Paginator
import secrets
import string

User = get_user_model()


def home(request):
    """
    Home page - redirects to dashboard if logged in, otherwise redirects to login.
    """
    if request.user.is_authenticated:
        return redirect('/dashboard/')
    return redirect('/login/')


def login_view(request):
    """
    Web-based login view.
    """
    if request.user.is_authenticated:
        return redirect('/dashboard/')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if email and password:
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, 'Successfully logged in!')
                return redirect('/dashboard/')
            else:
                messages.error(request, 'Invalid email or password.')
        else:
            messages.error(request, 'Please provide both email and password.')
    
    return render(request, 'core/login.html')


@login_required
def dashboard(request):
    """
    Main dashboard view.
    
    TODO: Phase 2 - Implement dashboard with metrics
    """
    return render(request, 'core/dashboard.html')


@login_required
def dashboard_overview(request):
    """
    Detailed account overview page showing account summary, connected Amazon accounts, and account health metrics.
    """
    from apps.accounts.models import Organization
    from apps.amazon_auth.models import AmazonAccount
    
    # Get user's organizations
    user_organizations = Organization.objects.filter(
        Q(owner=request.user) | Q(members=request.user)
    ).distinct()
    
    # Get connected Amazon accounts for user's organizations
    amazon_accounts = AmazonAccount.objects.filter(
        organization__in=user_organizations
    ).select_related('organization').order_by('-created_at')
    
    # Calculate account health metrics (placeholder - Phase 2 will implement real metrics)
    total_accounts = amazon_accounts.count()
    connected_accounts = amazon_accounts.filter(is_connected=True).count()
    active_accounts = amazon_accounts.filter(is_active=True).count()
    
    # Account health score (placeholder calculation)
    if total_accounts > 0:
        health_score = int((connected_accounts / total_accounts) * 100)
    else:
        health_score = 0
    
    # Prepare account summary
    account_summary = {
        'total_organizations': user_organizations.count(),
        'total_amazon_accounts': total_accounts,
        'connected_accounts': connected_accounts,
        'active_accounts': active_accounts,
        'health_score': health_score,
    }
    
    context = {
        'user': request.user,
        'organizations': user_organizations,
        'amazon_accounts': amazon_accounts,
        'account_summary': account_summary,
    }
    
    return render(request, 'core/dashboard_overview.html', context)


@login_required
def dashboard_spend(request):
    """
    Detailed spending analysis page showing daily/weekly/monthly spend breakdown, spend trends, and budget utilization.
    """
    from apps.accounts.models import Organization
    from apps.amazon_auth.models import AmazonAccount
    from apps.amazon_ads.models import Campaign, CampaignPerformance
    from django.db.models import Sum, Avg, Q
    from datetime import datetime, timedelta
    from decimal import Decimal
    
    # Get user's organizations
    user_organizations = Organization.objects.filter(
        Q(owner=request.user) | Q(members=request.user)
    ).distinct()
    
    # Get connected Amazon accounts for user's organizations
    amazon_accounts = AmazonAccount.objects.filter(
        organization__in=user_organizations,
        is_connected=True
    )
    
    # Get campaigns for connected accounts
    campaigns = Campaign.objects.filter(account__in=amazon_accounts)
    
    # Get date range (default to last 30 days)
    today = datetime.now().date()
    last_30_days = today - timedelta(days=30)
    last_7_days = today - timedelta(days=7)
    
    # Get performance data
    performance_data = CampaignPerformance.objects.filter(
        campaign__in=campaigns,
        date__gte=last_30_days
    ).order_by('date')
    
    # Calculate total spend
    total_spend = performance_data.aggregate(total=Sum('cost'))['total'] or Decimal('0.00')
    total_spend_7d = performance_data.filter(date__gte=last_7_days).aggregate(total=Sum('cost'))['total'] or Decimal('0.00')
    
    # Calculate daily spend breakdown (last 30 days)
    daily_spend = {}
    max_daily_spend = Decimal('0.00')
    for i in range(30):
        date = today - timedelta(days=i)
        day_spend = performance_data.filter(date=date).aggregate(total=Sum('cost'))['total'] or Decimal('0.00')
        daily_spend[date.isoformat()] = float(day_spend)
        if day_spend > max_daily_spend:
            max_daily_spend = day_spend
    
    # Calculate weekly spend breakdown (last 4 weeks)
    weekly_spend = []
    for week_num in range(4):
        week_start = today - timedelta(days=(week_num + 1) * 7)
        week_end = today - timedelta(days=week_num * 7)
        week_total = performance_data.filter(
            date__gte=week_start,
            date__lt=week_end
        ).aggregate(total=Sum('cost'))['total'] or Decimal('0.00')
        weekly_spend.append({
            'week': f"Week {4 - week_num}",
            'start_date': week_start,
            'end_date': week_end - timedelta(days=1),
            'spend': float(week_total)
        })
    
    # Calculate monthly spend breakdown (last 3 months)
    monthly_spend = []
    for month_num in range(3):
        month_start = today.replace(day=1) - timedelta(days=month_num * 30)
        if month_num == 0:
            month_end = today
        else:
            next_month = month_start.replace(day=28) + timedelta(days=4)
            month_end = (next_month - timedelta(days=next_month.day)).replace(day=1)
        
        month_total = performance_data.filter(
            date__gte=month_start,
            date__lt=month_end
        ).aggregate(total=Sum('cost'))['total'] or Decimal('0.00')
        monthly_spend.append({
            'month': month_start.strftime('%B %Y'),
            'start_date': month_start,
            'end_date': month_end - timedelta(days=1),
            'spend': float(month_total)
        })
    
    # Calculate budget utilization
    total_budget = campaigns.aggregate(total=Sum('daily_budget'))['total'] or Decimal('0.00')
    if total_budget > 0:
        # Calculate average daily budget
        avg_daily_budget = float(total_budget)
        # Calculate projected monthly budget (30 days)
        projected_monthly_budget = avg_daily_budget * 30
        # Calculate actual monthly spend
        actual_monthly_spend = float(total_spend)
        # Calculate remaining budget
        remaining_budget = max(projected_monthly_budget - actual_monthly_spend, 0)
        # Budget utilization percentage
        if projected_monthly_budget > 0:
            budget_utilization = min((actual_monthly_spend / projected_monthly_budget) * 100, 100)
        else:
            budget_utilization = 0
    else:
        avg_daily_budget = 0
        projected_monthly_budget = 0
        actual_monthly_spend = 0
        remaining_budget = 0
        budget_utilization = 0
    
    # Calculate spend trends (compare last 7 days vs previous 7 days)
    previous_7_days_start = last_7_days - timedelta(days=7)
    previous_7_days_spend = performance_data.filter(
        date__gte=previous_7_days_start,
        date__lt=last_7_days
    ).aggregate(total=Sum('cost'))['total'] or Decimal('0.00')
    
    if previous_7_days_spend > 0:
        spend_change_percent = ((float(total_spend_7d) - float(previous_7_days_spend)) / float(previous_7_days_spend)) * 100
        spend_change_percent_abs = abs(spend_change_percent)
    else:
        spend_change_percent = 0
        spend_change_percent_abs = 0
    
    # Top spending campaigns
    top_campaigns = campaigns.annotate(
        total_spend=Sum('performance_data__cost', filter=Q(performance_data__date__gte=last_30_days))
    ).order_by('-total_spend')[:10]
    
    context = {
        'total_spend': float(total_spend),
        'total_spend_7d': float(total_spend_7d),
        'spend_change_percent': spend_change_percent,
        'spend_change_percent_abs': spend_change_percent_abs,
        'daily_spend': daily_spend,
        'weekly_spend': weekly_spend,
        'monthly_spend': monthly_spend,
        'budget_utilization': budget_utilization,
        'avg_daily_budget': avg_daily_budget,
        'projected_monthly_budget': projected_monthly_budget,
        'actual_monthly_spend': actual_monthly_spend,
        'remaining_budget': remaining_budget,
        'total_budget': float(total_budget),
        'max_daily_spend': float(max_daily_spend),
        'top_campaigns': top_campaigns,
        'campaigns_count': campaigns.count(),
        'date_range': {
            'start': last_30_days,
            'end': today
        }
    }
    
    return render(request, 'core/dashboard_spend.html', context)


@login_required
def dashboard_sales(request):
    """
    Sales performance page showing revenue, sales trends, and conversion metrics.
    """
    from apps.accounts.models import Organization
    from apps.amazon_auth.models import AmazonAccount
    from apps.amazon_ads.models import Campaign, CampaignPerformance
    from django.db.models import Sum, Avg, Q, Count
    from datetime import datetime, timedelta
    from decimal import Decimal
    
    # Get user's organizations
    user_organizations = Organization.objects.filter(
        Q(owner=request.user) | Q(members=request.user)
    ).distinct()
    
    # Get connected Amazon accounts for user's organizations
    amazon_accounts = AmazonAccount.objects.filter(
        organization__in=user_organizations,
        is_connected=True
    )
    
    # Get campaigns for connected accounts
    campaigns = Campaign.objects.filter(account__in=amazon_accounts)
    
    # Get date range (default to last 30 days)
    today = datetime.now().date()
    last_30_days = today - timedelta(days=30)
    last_7_days = today - timedelta(days=7)
    
    # Get performance data
    performance_data = CampaignPerformance.objects.filter(
        campaign__in=campaigns,
        date__gte=last_30_days
    ).order_by('date')
    
    # Calculate total revenue/sales
    total_sales = performance_data.aggregate(total=Sum('sales'))['total'] or Decimal('0.00')
    total_sales_7d = performance_data.filter(date__gte=last_7_days).aggregate(total=Sum('sales'))['total'] or Decimal('0.00')
    total_orders = performance_data.aggregate(total=Sum('orders'))['total'] or 0
    total_units_sold = performance_data.aggregate(total=Sum('units_sold'))['total'] or 0
    
    # Calculate conversion metrics
    total_clicks = performance_data.aggregate(total=Sum('clicks'))['total'] or 0
    total_impressions = performance_data.aggregate(total=Sum('impressions'))['total'] or 0
    
    # Average conversion rate
    if total_clicks > 0:
        avg_cvr = (total_orders / total_clicks) * 100
    else:
        avg_cvr = 0
    
    # Average CTR (Click-through rate)
    if total_impressions > 0:
        avg_ctr = (total_clicks / total_impressions) * 100
    else:
        avg_ctr = 0
    
    # Average ROAS (Return on Ad Spend)
    total_spend = performance_data.aggregate(total=Sum('cost'))['total'] or Decimal('0.00')
    if total_spend > 0:
        avg_roas = float(total_sales) / float(total_spend)
    else:
        avg_roas = 0
    
    # Average ACOS (Advertising Cost of Sales)
    if total_sales > 0:
        avg_acos = (float(total_spend) / float(total_sales)) * 100
    else:
        avg_acos = 0
    
    # Store total_spend for template
    total_spend_value = float(total_spend)
    
    # Calculate daily sales breakdown (last 30 days)
    daily_sales = {}
    max_daily_sales = Decimal('0.00')
    for i in range(30):
        date = today - timedelta(days=i)
        day_sales = performance_data.filter(date=date).aggregate(total=Sum('sales'))['total'] or Decimal('0.00')
        daily_sales[date.isoformat()] = float(day_sales)
        if day_sales > max_daily_sales:
            max_daily_sales = day_sales
    
    # Calculate weekly sales breakdown (last 4 weeks)
    weekly_sales = []
    for week_num in range(4):
        week_start = today - timedelta(days=(week_num + 1) * 7)
        week_end = today - timedelta(days=week_num * 7)
        week_total = performance_data.filter(
            date__gte=week_start,
            date__lt=week_end
        ).aggregate(total=Sum('sales'))['total'] or Decimal('0.00')
        week_orders = performance_data.filter(
            date__gte=week_start,
            date__lt=week_end
        ).aggregate(total=Sum('orders'))['total'] or 0
        weekly_sales.append({
            'week': f"Week {4 - week_num}",
            'start_date': week_start,
            'end_date': week_end - timedelta(days=1),
            'sales': float(week_total),
            'orders': week_orders
        })
    
    # Calculate monthly sales breakdown (last 3 months)
    monthly_sales = []
    for month_num in range(3):
        month_start = today.replace(day=1) - timedelta(days=month_num * 30)
        if month_num == 0:
            month_end = today
        else:
            next_month = month_start.replace(day=28) + timedelta(days=4)
            month_end = (next_month - timedelta(days=next_month.day)).replace(day=1)
        
        month_total = performance_data.filter(
            date__gte=month_start,
            date__lt=month_end
        ).aggregate(total=Sum('sales'))['total'] or Decimal('0.00')
        month_orders = performance_data.filter(
            date__gte=month_start,
            date__lt=month_end
        ).aggregate(total=Sum('orders'))['total'] or 0
        monthly_sales.append({
            'month': month_start.strftime('%B %Y'),
            'start_date': month_start,
            'end_date': month_end - timedelta(days=1),
            'sales': float(month_total),
            'orders': month_orders
        })
    
    # Calculate sales trends (compare last 7 days vs previous 7 days)
    previous_7_days_start = last_7_days - timedelta(days=7)
    previous_7_days_sales = performance_data.filter(
        date__gte=previous_7_days_start,
        date__lt=last_7_days
    ).aggregate(total=Sum('sales'))['total'] or Decimal('0.00')
    
    if previous_7_days_sales > 0:
        sales_change_percent = ((float(total_sales_7d) - float(previous_7_days_sales)) / float(previous_7_days_sales)) * 100
        sales_change_percent_abs = abs(sales_change_percent)
    else:
        sales_change_percent = 0
        sales_change_percent_abs = 0
    
    # Top performing campaigns by sales
    top_campaigns = campaigns.annotate(
        total_sales=Sum('performance_data__sales', filter=Q(performance_data__date__gte=last_30_days)),
        total_orders=Sum('performance_data__orders', filter=Q(performance_data__date__gte=last_30_days))
    ).order_by('-total_sales')[:10]
    
    context = {
        'total_sales': float(total_sales),
        'total_sales_7d': float(total_sales_7d),
        'sales_change_percent': sales_change_percent,
        'sales_change_percent_abs': sales_change_percent_abs,
        'total_orders': total_orders,
        'total_units_sold': total_units_sold,
        'total_clicks': total_clicks,
        'total_impressions': total_impressions,
        'avg_cvr': avg_cvr,
        'avg_ctr': avg_ctr,
        'avg_roas': avg_roas,
        'avg_acos': avg_acos,
        'total_spend': total_spend_value,
        'daily_sales': daily_sales,
        'max_daily_sales': float(max_daily_sales),
        'weekly_sales': weekly_sales,
        'monthly_sales': monthly_sales,
        'top_campaigns': top_campaigns,
        'campaigns_count': campaigns.count(),
        'date_range': {
            'start': last_30_days,
            'end': today
        }
    }
    
    return render(request, 'core/dashboard_sales.html', context)


@login_required
def dashboard_acos(request):
    """
    ACOS (Advertising Cost of Sale) analysis page showing ACOS trends, 
    target vs actual ACOS, and optimization recommendations.
    """
    from apps.accounts.models import Organization
    from apps.amazon_auth.models import AmazonAccount
    from apps.amazon_ads.models import Campaign, CampaignPerformance, KeywordPerformance
    from apps.autopilot.models import AutopilotGoal
    from django.db.models import Sum, Avg, Q, Count, F
    from datetime import datetime, timedelta
    from decimal import Decimal
    
    # Get user's organizations
    user_organizations = Organization.objects.filter(
        Q(owner=request.user) | Q(members=request.user)
    ).distinct()
    
    # Get connected Amazon accounts for user's organizations
    amazon_accounts = AmazonAccount.objects.filter(
        organization__in=user_organizations,
        is_connected=True
    )
    
    # Get campaigns for connected accounts
    campaigns = Campaign.objects.filter(account__in=amazon_accounts)
    
    # Get date range (default to last 30 days)
    today = datetime.now().date()
    last_30_days = today - timedelta(days=30)
    last_7_days = today - timedelta(days=7)
    
    # Get performance data
    performance_data = CampaignPerformance.objects.filter(
        campaign__in=campaigns,
        date__gte=last_30_days
    ).order_by('date')
    
    # Calculate average ACOS (use stored ACOS or calculate from cost/sales)
    acos_data = []
    total_cost = Decimal('0.00')
    total_sales = Decimal('0.00')
    
    for perf in performance_data:
        if perf.acos is not None:
            acos_data.append(float(perf.acos))
        elif perf.sales > 0:
            calculated_acos = (float(perf.cost) / float(perf.sales)) * 100
            acos_data.append(calculated_acos)
        total_cost += perf.cost
        total_sales += perf.sales
    
    # Overall average ACOS
    if acos_data:
        avg_acos = sum(acos_data) / len(acos_data)
    elif total_sales > 0:
        avg_acos = (float(total_cost) / float(total_sales)) * 100
    else:
        avg_acos = 0
    
    # Get target ACOS from autopilot goals (use first active goal with target_acos, or default to 30%)
    target_acos_goal = AutopilotGoal.objects.filter(
        account__in=amazon_accounts,
        is_active=True,
        target_acos__isnull=False
    ).first()
    
    if target_acos_goal and target_acos_goal.target_acos:
        target_acos = float(target_acos_goal.target_acos)
    else:
        target_acos = 30.0  # Default target
    
    # Calculate ACOS variance
    acos_variance = avg_acos - target_acos
    acos_variance_abs = abs(acos_variance)
    acos_variance_percent = (acos_variance / target_acos) * 100 if target_acos > 0 else 0
    
    # Calculate daily ACOS breakdown (last 30 days)
    daily_acos = {}
    max_daily_acos = 0
    for i in range(30):
        date = today - timedelta(days=i)
        day_perf = performance_data.filter(date=date)
        day_cost = day_perf.aggregate(total=Sum('cost'))['total'] or Decimal('0.00')
        day_sales = day_perf.aggregate(total=Sum('sales'))['total'] or Decimal('0.00')
        if day_sales > 0:
            day_acos = (float(day_cost) / float(day_sales)) * 100
        else:
            day_acos = 0
        daily_acos[date.isoformat()] = day_acos
        if day_acos > max_daily_acos:
            max_daily_acos = day_acos
    
    # Calculate weekly ACOS breakdown (last 4 weeks)
    weekly_acos = []
    for week_num in range(4):
        week_start = today - timedelta(days=(week_num + 1) * 7)
        week_end = today - timedelta(days=week_num * 7)
        week_perf = performance_data.filter(
            date__gte=week_start,
            date__lt=week_end
        )
        week_cost = week_perf.aggregate(total=Sum('cost'))['total'] or Decimal('0.00')
        week_sales = week_perf.aggregate(total=Sum('sales'))['total'] or Decimal('0.00')
        if week_sales > 0:
            week_acos_value = (float(week_cost) / float(week_sales)) * 100
        else:
            week_acos_value = 0
        weekly_acos.append({
            'week': f"Week {4 - week_num}",
            'start_date': week_start,
            'end_date': week_end - timedelta(days=1),
            'acos': week_acos_value,
            'cost': float(week_cost),
            'sales': float(week_sales),
            'variance': week_acos_value - target_acos
        })
    
    # Calculate monthly ACOS breakdown (last 3 months)
    monthly_acos = []
    for month_num in range(3):
        month_start = today.replace(day=1) - timedelta(days=month_num * 30)
        if month_num == 0:
            month_end = today
        else:
            next_month = month_start.replace(day=28) + timedelta(days=4)
            month_end = (next_month - timedelta(days=next_month.day)).replace(day=1)
        
        month_perf = performance_data.filter(
            date__gte=month_start,
            date__lt=month_end
        )
        month_cost = month_perf.aggregate(total=Sum('cost'))['total'] or Decimal('0.00')
        month_sales = month_perf.aggregate(total=Sum('sales'))['total'] or Decimal('0.00')
        if month_sales > 0:
            month_acos_value = (float(month_cost) / float(month_sales)) * 100
        else:
            month_acos_value = 0
        monthly_acos.append({
            'month': month_start.strftime('%B %Y'),
            'start_date': month_start,
            'end_date': month_end - timedelta(days=1),
            'acos': month_acos_value,
            'cost': float(month_cost),
            'sales': float(month_sales),
            'variance': month_acos_value - target_acos
        })
    
    # Get campaigns with high ACOS (above target)
    campaigns_with_acos = campaigns.annotate(
        total_cost=Sum('performance_data__cost', filter=Q(performance_data__date__gte=last_30_days)),
        total_sales=Sum('performance_data__sales', filter=Q(performance_data__date__gte=last_30_days))
    ).filter(
        total_sales__gt=0
    )
    
    high_acos_campaigns = []
    for campaign in campaigns_with_acos:
        if campaign.total_sales > 0:
            campaign_acos = (float(campaign.total_cost or 0) / float(campaign.total_sales)) * 100
            if campaign_acos > target_acos:
                high_acos_campaigns.append({
                    'campaign': campaign,
                    'acos': campaign_acos,
                    'cost': float(campaign.total_cost or 0),
                    'sales': float(campaign.total_sales),
                    'variance': campaign_acos - target_acos
                })
    
    # Sort by ACOS descending
    high_acos_campaigns.sort(key=lambda x: x['acos'], reverse=True)
    high_acos_campaigns = high_acos_campaigns[:10]  # Top 10
    
    # Count campaigns over target
    campaigns_over_target = len(high_acos_campaigns)
    total_active_campaigns = campaigns_with_acos.count()
    
    # Generate optimization recommendations
    recommendations = []
    
    # Recommendation 1: Overall ACOS status
    if avg_acos > target_acos * 1.2:  # 20% over target
        recommendations.append({
            'priority': 'high',
            'title': 'Overall ACOS is significantly above target',
            'description': f'Your average ACOS ({avg_acos:.2f}%) is {acos_variance:.2f}% above your target ({target_acos:.2f}%). Consider reviewing and optimizing underperforming campaigns.',
            'action': 'Review high ACOS campaigns and adjust bids or pause underperforming keywords.'
        })
    elif avg_acos > target_acos:
        recommendations.append({
            'priority': 'medium',
            'title': 'ACOS slightly above target',
            'description': f'Your average ACOS ({avg_acos:.2f}%) is {acos_variance:.2f}% above your target ({target_acos:.2f}%).',
            'action': 'Monitor campaigns closely and consider minor bid adjustments.'
        })
    else:
        recommendations.append({
            'priority': 'low',
            'title': 'ACOS is within target range',
            'description': f'Your average ACOS ({avg_acos:.2f}%) is below your target ({target_acos:.2f}%). Great job!',
            'action': 'Consider scaling successful campaigns to increase sales volume.'
        })
    
    # Recommendation 2: High ACOS campaigns
    if campaigns_over_target > 0:
        recommendations.append({
            'priority': 'high',
            'title': f'{campaigns_over_target} campaigns exceed target ACOS',
            'description': f'{campaigns_over_target} out of {total_active_campaigns} campaigns have ACOS above your target. These campaigns need immediate attention.',
            'action': 'Review the high ACOS campaigns list and optimize bids, add negative keywords, or pause underperforming ad groups.'
        })
    
    # Recommendation 3: ACOS trend
    if len(weekly_acos) >= 2:
        recent_trend = weekly_acos[0]['acos'] - weekly_acos[1]['acos']
        if recent_trend > 5:  # ACOS increased by more than 5%
            recommendations.append({
                'priority': 'high',
                'title': 'ACOS is trending upward',
                'description': f'Your ACOS has increased by {recent_trend:.2f}% in the last week. This may indicate increased competition or less efficient spending.',
                'action': 'Review recent changes, check for new competitors, and consider adjusting bidding strategies.'
            })
        elif recent_trend < -5:  # ACOS decreased by more than 5%
            recommendations.append({
                'priority': 'low',
                'title': 'ACOS is improving',
                'description': f'Your ACOS has decreased by {abs(recent_trend):.2f}% in the last week. Your optimization efforts are working!',
                'action': 'Continue monitoring and consider applying similar strategies to other campaigns.'
            })
    
    # Recommendation 4: Low sales volume
    if total_sales < 100:  # Less than $100 in sales
        recommendations.append({
            'priority': 'medium',
            'title': 'Low sales volume detected',
            'description': f'Total sales in the last 30 days are ${total_sales:.2f}. Low sales volume can make ACOS calculations less reliable.',
            'action': 'Focus on increasing impressions and clicks to generate more sales data for accurate ACOS analysis.'
        })
    
    # Recommendation 5: No target ACOS set
    if not target_acos_goal:
        recommendations.append({
            'priority': 'medium',
            'title': 'No target ACOS configured',
            'description': 'You haven\'t set a target ACOS in your Autopilot goals. Setting a target helps track performance and enables automated optimization.',
            'action': 'Go to Autopilot settings and configure a target ACOS goal for your campaigns.'
        })
    
    context = {
        'avg_acos': avg_acos,
        'target_acos': target_acos,
        'acos_variance': acos_variance,
        'acos_variance_abs': acos_variance_abs,
        'acos_variance_percent': acos_variance_percent,
        'campaigns_over_target': campaigns_over_target,
        'total_active_campaigns': total_active_campaigns,
        'daily_acos': daily_acos,
        'max_daily_acos': max_daily_acos,
        'weekly_acos': weekly_acos,
        'monthly_acos': monthly_acos,
        'high_acos_campaigns': high_acos_campaigns,
        'recommendations': recommendations,
        'total_cost': float(total_cost),
        'total_sales': float(total_sales),
        'date_range': {
            'start': last_30_days,
            'end': today
        }
    }
    
    return render(request, 'core/dashboard_acos.html', context)


@login_required
def dashboard_autopilot_status(request):
    """
    Autopilot status overview showing active rules, recent actions, and autopilot health metrics.
    """
    from apps.accounts.models import Organization
    from apps.amazon_auth.models import AmazonAccount
    from apps.autopilot.models import AutopilotGoal, AutomationRule, AutopilotExecution, SafetyLimit
    from django.db.models import Count, Q
    from datetime import datetime, timedelta
    
    # Get user's organizations
    user_organizations = Organization.objects.filter(
        Q(owner=request.user) | Q(members=request.user)
    ).distinct()
    
    # Get connected Amazon accounts for user's organizations
    amazon_accounts = AmazonAccount.objects.filter(
        organization__in=user_organizations,
        is_connected=True
    )
    
    # Get autopilot goals
    goals = AutopilotGoal.objects.filter(account__in=amazon_accounts)
    active_goals = goals.filter(is_active=True)
    
    # Get automation rules
    rules = AutomationRule.objects.filter(goal__account__in=amazon_accounts)
    active_rules = rules.filter(is_active=True)
    
    # Get recent executions (last 30 days)
    today = datetime.now()
    last_30_days = today - timedelta(days=30)
    recent_executions = AutopilotExecution.objects.filter(
        account__in=amazon_accounts,
        executed_at__gte=last_30_days
    ).order_by('-executed_at')[:50]
    
    # Get safety limits
    safety_limits = SafetyLimit.objects.filter(account__in=amazon_accounts)
    
    # Calculate health metrics
    total_goals = goals.count()
    total_active_goals = active_goals.count()
    total_rules = rules.count()
    total_active_rules = active_rules.count()
    
    # Execution statistics (last 30 days)
    execution_stats = AutopilotExecution.objects.filter(
        account__in=amazon_accounts,
        executed_at__gte=last_30_days
    ).aggregate(
        total_executions=Count('id'),
        executed=Count('id', filter=Q(status='executed')),
        skipped=Count('id', filter=Q(status='skipped')),
        failed=Count('id', filter=Q(status='failed')),
        blocked=Count('id', filter=Q(status='blocked'))
    )
    
    total_executions = execution_stats['total_executions'] or 0
    executed_count = execution_stats['executed'] or 0
    skipped_count = execution_stats['skipped'] or 0
    failed_count = execution_stats['failed'] or 0
    blocked_count = execution_stats['blocked'] or 0
    
    # Calculate success rate
    if total_executions > 0:
        success_rate = (executed_count / total_executions) * 100
    else:
        success_rate = 0
    
    # Safety limits status
    safety_enabled_count = safety_limits.filter(is_enabled=True).count()
    total_safety_limits = safety_limits.count()
    
    # Get executions by status for chart
    executions_by_status = {
        'executed': executed_count,
        'skipped': skipped_count,
        'failed': failed_count,
        'blocked': blocked_count
    }
    max_executions = max(executions_by_status.values()) if executions_by_status.values() else 1
    
    # Get recent executions by day (last 7 days)
    daily_executions = {}
    for i in range(7):
        date = (today - timedelta(days=i)).date()
        day_count = AutopilotExecution.objects.filter(
            account__in=amazon_accounts,
            executed_at__date=date
        ).count()
        daily_executions[date.isoformat()] = day_count
    
    # Get rules by type
    rules_by_type = active_rules.values('rule_type').annotate(count=Count('id')).order_by('-count')
    
    # Get most active rules (by execution count)
    most_active_rules = active_rules.annotate(
        execution_count=Count('executions', filter=Q(executions__executed_at__gte=last_30_days))
    ).order_by('-execution_count')[:10]
    
    # Health status
    health_status = 'healthy'
    health_issues = []
    
    if total_active_goals == 0:
        health_status = 'warning'
        health_issues.append('No active autopilot goals configured')
    
    if total_active_rules == 0:
        health_status = 'warning'
        health_issues.append('No active automation rules')
    
    if failed_count > 0 and total_executions > 0:
        failure_rate = (failed_count / total_executions) * 100
        if failure_rate > 10:  # More than 10% failure rate
            health_status = 'error'
            health_issues.append(f'High failure rate: {failure_rate:.1f}%')
        elif failure_rate > 5:
            health_status = 'warning'
            health_issues.append(f'Moderate failure rate: {failure_rate:.1f}%')
    
    if safety_enabled_count < total_safety_limits:
        health_status = 'warning'
        health_issues.append('Some safety limits are disabled')
    
    # Get account-level summary
    account_summaries = []
    for account in amazon_accounts:
        account_goals = goals.filter(account=account)
        account_active_goals = account_goals.filter(is_active=True)
        account_rules = rules.filter(goal__account=account)
        account_active_rules = account_rules.filter(is_active=True)
        account_executions = AutopilotExecution.objects.filter(
            account=account,
            executed_at__gte=last_30_days
        )
        account_safety = safety_limits.filter(account=account).first()
        
        account_summaries.append({
            'account': account,
            'total_goals': account_goals.count(),
            'active_goals': account_active_goals.count(),
            'total_rules': account_rules.count(),
            'active_rules': account_active_rules.count(),
            'executions_30d': account_executions.count(),
            'safety_enabled': account_safety.is_enabled if account_safety else True
        })
    
    context = {
        'goals': active_goals,
        'total_goals': total_goals,
        'total_active_goals': total_active_goals,
        'rules': active_rules,
        'total_rules': total_rules,
        'total_active_rules': total_active_rules,
        'recent_executions': recent_executions,
        'total_executions': total_executions,
        'executed_count': executed_count,
        'skipped_count': skipped_count,
        'failed_count': failed_count,
        'blocked_count': blocked_count,
        'success_rate': success_rate,
        'executions_by_status': executions_by_status,
        'max_executions': max_executions,
        'daily_executions': daily_executions,
        'rules_by_type': rules_by_type,
        'most_active_rules': most_active_rules,
        'safety_limits': safety_limits,
        'safety_enabled_count': safety_enabled_count,
        'total_safety_limits': total_safety_limits,
        'health_status': health_status,
        'health_issues': health_issues,
        'account_summaries': account_summaries,
        'date_range': {
            'start': last_30_days,
            'end': today
        }
    }
    
    return render(request, 'core/dashboard_autopilot_status.html', context)


@login_required
def autopilot_overview(request):
    """
    Main autopilot dashboard showing autopilot status, active rules, recent actions, and performance summary.
    """
    from apps.accounts.models import Organization
    from apps.amazon_auth.models import AmazonAccount
    from apps.autopilot.models import AutopilotGoal, AutomationRule, AutopilotExecution, SafetyLimit
    from django.db.models import Count, Q
    from datetime import datetime, timedelta

    # Get user's organizations
    user_organizations = Organization.objects.filter(
        Q(owner=request.user) | Q(members=request.user)
    ).distinct()

    # Get connected Amazon accounts for user's organizations
    amazon_accounts = AmazonAccount.objects.filter(
        organization__in=user_organizations,
        is_connected=True
    )

    # Check if autopilot is globally enabled (at least one account has safety limits enabled)
    autopilot_enabled = SafetyLimit.objects.filter(
        account__in=amazon_accounts,
        is_enabled=True
    ).exists()

    # Get active goals and rules
    active_goals = AutopilotGoal.objects.filter(
        account__in=amazon_accounts,
        is_active=True
    )
    active_rules = AutomationRule.objects.filter(
        goal__account__in=amazon_accounts,
        is_active=True
    )

    # Get recent executions (last 7 days for quick overview)
    today = datetime.now()
    last_7_days = today - timedelta(days=7)
    recent_executions = AutopilotExecution.objects.filter(
        account__in=amazon_accounts,
        executed_at__gte=last_7_days
    ).order_by('-executed_at')[:10]  # Last 10 actions

    # Calculate quick stats
    total_accounts = amazon_accounts.count()
    total_active_goals = active_goals.count()
    total_active_rules = active_rules.count()

    # Execution stats for last 7 days
    execution_stats = AutopilotExecution.objects.filter(
        account__in=amazon_accounts,
        executed_at__gte=last_7_days
    ).aggregate(
        total_executions=Count('id'),
        executed=Count('id', filter=Q(status='executed')),
        failed=Count('id', filter=Q(status='failed'))
    )

    executions_last_7d = execution_stats['total_executions'] or 0
    successful_executions = execution_stats['executed'] or 0

    # Calculate success rate
    if executions_last_7d > 0:
        success_rate = (successful_executions / executions_last_7d) * 100
    else:
        success_rate = 0

    # Get performance impact (simplified - showing recent changes)
    # This would be more complex in a real implementation
    performance_impact = {
        'spend_change': 0,  # Placeholder - would calculate actual impact
        'acos_change': 0,   # Placeholder - would calculate actual impact
        'sales_change': 0    # Placeholder - would calculate actual impact
    }

    # Get rules by type for breakdown
    rules_by_type_raw = active_rules.values('rule_type').annotate(
        count=Count('id')
    ).order_by('-count')

    # Add display names for rule types
    RULE_TYPE_DISPLAY_NAMES = {
        'keyword_bid': 'Keyword Bid Adjustment',
        'keyword_pause': 'Pause Keyword',
        'keyword_enable': 'Enable Keyword',
        'campaign_budget': 'Campaign Budget Adjustment',
        'campaign_pause': 'Pause Campaign',
        'negative_keyword': 'Add Negative Keyword',
    }

    rules_by_type = []
    for rule_type_data in rules_by_type_raw:
        display_name = RULE_TYPE_DISPLAY_NAMES.get(
            rule_type_data['rule_type'],
            rule_type_data['rule_type'].replace('_', ' ').title()
        )
        rules_by_type.append({
            'rule_type': rule_type_data['rule_type'],
            'display_name': display_name,
            'count': rule_type_data['count']
        })

    # Health status
    health_status = 'healthy'
    health_message = 'All systems operational'

    if not autopilot_enabled:
        health_status = 'inactive'
        health_message = 'Autopilot is currently disabled'
    elif total_active_goals == 0:
        health_status = 'warning'
        health_message = 'No active goals configured'
    elif total_active_rules == 0:
        health_status = 'warning'
        health_message = 'No active rules configured'
    elif executions_last_7d > 0 and success_rate < 80:
        health_status = 'warning'
        health_message = f'Low success rate: {success_rate:.1f}%'

    context = {
        'autopilot_enabled': autopilot_enabled,
        'total_accounts': total_accounts,
        'total_active_goals': total_active_goals,
        'total_active_rules': total_active_rules,
        'executions_last_7d': executions_last_7d,
        'successful_executions': successful_executions,
        'success_rate': success_rate,
        'performance_impact': performance_impact,
        'rules_by_type': rules_by_type,
        'recent_executions': recent_executions,
        'health_status': health_status,
        'health_message': health_message,
        'date_range': {
            'start': last_7_days,
            'end': today
        }
    }

    return render(request, 'core/autopilot.html', context)


@login_required
def autopilot_goals(request):
    """
    Goals & Targets configuration page for setting autopilot objectives.
    Features: Goal types (Profit, Growth, Rank), Target ACOS/ROAS setting, Budget goals, Priority settings.
    """
    from apps.accounts.models import Organization
    from apps.amazon_auth.models import AmazonAccount
    from apps.autopilot.models import AutopilotGoal
    from django.shortcuts import redirect, get_object_or_404
    from django.contrib import messages

    # Get user's organizations
    user_organizations = Organization.objects.filter(
        Q(owner=request.user) | Q(members=request.user)
    ).distinct()

    # Get connected Amazon accounts
    amazon_accounts = AmazonAccount.objects.filter(
        organization__in=user_organizations,
        is_connected=True
    )

    # Handle POST requests (Create, Update, Delete)
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create':
            # Create new goal
            try:
                account_id = request.POST.get('account')
                account = get_object_or_404(AmazonAccount, id=account_id, organization__in=user_organizations)

                goal = AutopilotGoal.objects.create(
                    account=account,
                    name=request.POST.get('name'),
                    goal_type=request.POST.get('goal_type'),
                    is_active=request.POST.get('is_active') == 'on',
                    target_acos=request.POST.get('target_acos') or None,
                    target_roas=request.POST.get('target_roas') or None,
                    applies_to_all_campaigns=request.POST.get('applies_to_all_campaigns') == 'on',
                )
                messages.success(request, f'Goal "{goal.name}" created successfully.')
            except Exception as e:
                messages.error(request, f'Error creating goal: {str(e)}')

        elif action == 'update':
            # Update existing goal
            try:
                goal_id = request.POST.get('goal_id')
                goal = get_object_or_404(AutopilotGoal, id=goal_id, account__organization__in=user_organizations)

                goal.name = request.POST.get('name')
                goal.goal_type = request.POST.get('goal_type')
                goal.is_active = request.POST.get('is_active') == 'on'
                goal.target_acos = request.POST.get('target_acos') or None
                goal.target_roas = request.POST.get('target_roas') or None
                goal.applies_to_all_campaigns = request.POST.get('applies_to_all_campaigns') == 'on'

                goal.save()
                messages.success(request, f'Goal "{goal.name}" updated successfully.')
            except Exception as e:
                messages.error(request, f'Error updating goal: {str(e)}')

        elif action == 'delete':
            # Delete goal
            try:
                goal_id = request.POST.get('goal_id')
                goal = get_object_or_404(AutopilotGoal, id=goal_id, account__organization__in=user_organizations)
                goal_name = goal.name
                goal.delete()
                messages.success(request, f'Goal "{goal_name}" deleted successfully.')
            except Exception as e:
                messages.error(request, f'Error deleting goal: {str(e)}')

        elif action == 'toggle':
            # Toggle goal active status
            try:
                goal_id = request.POST.get('goal_id')
                goal = get_object_or_404(AutopilotGoal, id=goal_id, account__organization__in=user_organizations)
                goal.is_active = not goal.is_active
                goal.save()
                status = "activated" if goal.is_active else "deactivated"
                messages.success(request, f'Goal "{goal.name}" {status} successfully.')
            except Exception as e:
                messages.error(request, f'Error toggling goal: {str(e)}')

        return redirect('autopilot_goals')

    # Get all goals for user's accounts
    goals = AutopilotGoal.objects.filter(account__in=amazon_accounts).select_related('account').order_by('-created_at')

    # Goal type choices for display
    GOAL_TYPE_CHOICES = {
        'profit': 'Maximize Profit',
        'growth': 'Maximize Growth',
        'rank': 'Improve Ranking',
        'acos': 'Target ACOS',
        'roas': 'Target ROAS',
    }

    # Add display names to goals
    goals_with_display = []
    for goal in goals:
        goal.display_goal_type = GOAL_TYPE_CHOICES.get(goal.goal_type, goal.goal_type.replace('_', ' ').title())
        goals_with_display.append(goal)

    context = {
        'goals': goals_with_display,
        'amazon_accounts': amazon_accounts,
        'goal_type_choices': GOAL_TYPE_CHOICES,
    }

    return render(request, 'core/autopilot_goals.html', context)


@login_required
def autopilot_rules_engine(request):
    """
    Rules Engine configuration page for creating and managing automation rules.
    Features: Rule list, Create/Edit rules, Rule conditions (IF/THEN logic), Rule priority, Enable/Disable rules, Rule templates.
    """
    from apps.accounts.models import Organization
    from apps.amazon_auth.models import AmazonAccount
    from apps.autopilot.models import AutomationRule, AutopilotGoal
    from django.shortcuts import redirect, get_object_or_404
    from django.contrib import messages

    # Get user's organizations
    user_organizations = Organization.objects.filter(
        Q(owner=request.user) | Q(members=request.user)
    ).distinct()

    # Get connected Amazon accounts
    amazon_accounts = AmazonAccount.objects.filter(
        organization__in=user_organizations,
        is_connected=True
    )

    # Handle POST requests (Create, Update, Delete, Toggle)
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create':
            # Create new rule
            try:
                goal_id = request.POST.get('goal')
                goal = get_object_or_404(AutopilotGoal, id=goal_id, account__organization__in=user_organizations)

                rule = AutomationRule.objects.create(
                    goal=goal,
                    name=request.POST.get('name'),
                    rule_type=request.POST.get('rule_type'),
                    priority=int(request.POST.get('priority', 0)),
                    is_active=request.POST.get('is_active') == 'on',
                    condition_metric=request.POST.get('condition_metric'),
                    condition_operator=request.POST.get('condition_operator'),
                    condition_value=request.POST.get('condition_value'),
                    lookback_days=int(request.POST.get('lookback_days', 7)),
                    action_value=request.POST.get('action_value') or None,
                    action_percentage=request.POST.get('action_percentage') or None,
                    max_bid_change_percent=request.POST.get('max_bid_change_percent') or None,
                    min_bid=request.POST.get('min_bid') or None,
                    max_bid=request.POST.get('max_bid') or None,
                )
                messages.success(request, f'Rule "{rule.name}" created successfully.')
            except Exception as e:
                messages.error(request, f'Error creating rule: {str(e)}')

        elif action == 'update':
            # Update existing rule
            try:
                rule_id = request.POST.get('rule_id')
                rule = get_object_or_404(AutomationRule, id=rule_id, goal__account__organization__in=user_organizations)

                rule.name = request.POST.get('name')
                rule.rule_type = request.POST.get('rule_type')
                rule.priority = int(request.POST.get('priority', 0))
                rule.is_active = request.POST.get('is_active') == 'on'
                rule.condition_metric = request.POST.get('condition_metric')
                rule.condition_operator = request.POST.get('condition_operator')
                rule.condition_value = request.POST.get('condition_value')
                rule.lookback_days = int(request.POST.get('lookback_days', 7))
                rule.action_value = request.POST.get('action_value') or None
                rule.action_percentage = request.POST.get('action_percentage') or None
                rule.max_bid_change_percent = request.POST.get('max_bid_change_percent') or None
                rule.min_bid = request.POST.get('min_bid') or None
                rule.max_bid = request.POST.get('max_bid') or None

                rule.save()
                messages.success(request, f'Rule "{rule.name}" updated successfully.')
            except Exception as e:
                messages.error(request, f'Error updating rule: {str(e)}')

        elif action == 'delete':
            # Delete rule
            try:
                rule_id = request.POST.get('rule_id')
                rule = get_object_or_404(AutomationRule, id=rule_id, goal__account__organization__in=user_organizations)
                rule_name = rule.name
                rule.delete()
                messages.success(request, f'Rule "{rule_name}" deleted successfully.')
            except Exception as e:
                messages.error(request, f'Error deleting rule: {str(e)}')

        elif action == 'toggle':
            # Toggle rule active status
            try:
                rule_id = request.POST.get('rule_id')
                rule = get_object_or_404(AutomationRule, id=rule_id, goal__account__organization__in=user_organizations)
                rule.is_active = not rule.is_active
                rule.save()
                status = "activated" if rule.is_active else "deactivated"
                messages.success(request, f'Rule "{rule.name}" {status} successfully.')
            except Exception as e:
                messages.error(request, f'Error toggling rule: {str(e)}')

        return redirect('autopilot_rules_engine')

    # Get all rules for user's accounts
    rules = AutomationRule.objects.filter(
        goal__account__in=amazon_accounts
    ).select_related('goal', 'goal__account').order_by('-priority', '-created_at')

    # Get goals for rule creation
    goals = AutopilotGoal.objects.filter(account__in=amazon_accounts)

    # Rule type choices for display
    RULE_TYPE_CHOICES = {
        'keyword_bid': 'Keyword Bid Adjustment',
        'keyword_pause': 'Pause Keyword',
        'keyword_enable': 'Enable Keyword',
        'campaign_budget': 'Campaign Budget Adjustment',
        'campaign_pause': 'Pause Campaign',
        'negative_keyword': 'Add Negative Keyword',
    }

    CONDITION_METRIC_CHOICES = {
        'spend': 'Spend',
        'sales': 'Sales',
        'acos': 'ACOS',
        'roas': 'ROAS',
        'clicks': 'Clicks',
        'impressions': 'Impressions',
        'ctr': 'CTR',
        'conversions': 'Conversions',
        'orders': 'Orders',
    }

    CONDITION_OPERATOR_CHOICES = {
        'gt': 'Greater Than (>)',
        'gte': 'Greater Than or Equal (>=)',
        'lt': 'Less Than (<)',
        'lte': 'Less Than or Equal (<=)',
        'eq': 'Equals (=)',
        'ne': 'Not Equals (!=)',
    }

    # Add display names to rules
    rules_with_display = []
    for rule in rules:
        rule.display_rule_type = RULE_TYPE_CHOICES.get(rule.rule_type, rule.rule_type.replace('_', ' ').title())
        rule.display_condition_metric = CONDITION_METRIC_CHOICES.get(rule.condition_metric, rule.condition_metric.upper())
        rule.display_condition_operator = CONDITION_OPERATOR_CHOICES.get(rule.condition_operator, rule.condition_operator.upper())
        rules_with_display.append(rule)

    context = {
        'rules': rules_with_display,
        'goals': goals,
        'rule_type_choices': RULE_TYPE_CHOICES,
        'condition_metric_choices': CONDITION_METRIC_CHOICES,
        'condition_operator_choices': CONDITION_OPERATOR_CHOICES,
    }

    return render(request, 'core/autopilot_rules_engine.html', context)


@login_required
def autopilot_safety_controls(request):
    """
    Safety Controls configuration page for setting limits and safeguards for autopilot actions.
    Features: Max bid change per day, Budget caps, Manual override settings, Kill switch, Approval workflows, Safety configuration.
    """
    from apps.accounts.models import Organization
    from apps.amazon_auth.models import AmazonAccount
    from apps.autopilot.models import SafetyLimit
    from django.shortcuts import redirect, get_object_or_404
    from django.contrib import messages

    # Get user's organizations
    user_organizations = Organization.objects.filter(
        Q(owner=request.user) | Q(members=request.user)
    ).distinct()

    # Get connected Amazon accounts
    amazon_accounts = AmazonAccount.objects.filter(
        organization__in=user_organizations,
        is_connected=True
    )

    # Handle POST requests (Update safety limits)
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_safety':
            # Update or create safety limits for each account
            try:
                for account in amazon_accounts:
                    # Get or create safety limits for this account
                    safety_limit, created = SafetyLimit.objects.get_or_create(
                        account=account,
                        defaults={
                            'max_bid_changes_per_day': 50,
                            'max_budget_changes_per_day': 10,
                            'max_campaign_pauses_per_day': 5,
                            'max_daily_budget_increase_percent': Decimal('50'),
                            'max_daily_budget_decrease_percent': Decimal('30'),
                            'is_enabled': True,
                        }
                    )

                    # Update the safety limits
                    safety_limit.max_bid_changes_per_day = int(request.POST.get(f'max_bid_changes_{account.id}', 50))
                    safety_limit.max_budget_changes_per_day = int(request.POST.get(f'max_budget_changes_{account.id}', 10))
                    safety_limit.max_campaign_pauses_per_day = int(request.POST.get(f'max_campaign_pauses_{account.id}', 5))
                    safety_limit.max_daily_budget_increase_percent = Decimal(request.POST.get(f'max_budget_increase_{account.id}', '50'))
                    safety_limit.max_daily_budget_decrease_percent = Decimal(request.POST.get(f'max_budget_decrease_{account.id}', '30'))
                    safety_limit.is_enabled = request.POST.get(f'is_enabled_{account.id}') == 'on'

                    safety_limit.save()

                messages.success(request, 'Safety controls updated successfully.')
            except Exception as e:
                messages.error(request, f'Error updating safety controls: {str(e)}')

        elif action == 'global_kill_switch':
            # Global kill switch - disable all autopilot
            try:
                SafetyLimit.objects.filter(account__in=amazon_accounts).update(is_enabled=False)
                messages.warning(request, 'Global kill switch activated. All autopilot functionality has been disabled.')
            except Exception as e:
                messages.error(request, f'Error activating kill switch: {str(e)}')

        elif action == 'global_enable':
            # Global enable - enable all autopilot
            try:
                SafetyLimit.objects.filter(account__in=amazon_accounts).update(is_enabled=True)
                messages.success(request, 'All autopilot functionality has been enabled.')
            except Exception as e:
                messages.error(request, f'Error enabling autopilot: {str(e)}')

        return redirect('autopilot_safety_controls')

    # Get safety limits for all accounts
    accounts_with_limits = []
    for account in amazon_accounts:
        safety_limit, created = SafetyLimit.objects.get_or_create(
            account=account,
            defaults={
                'max_bid_changes_per_day': 50,
                'max_budget_changes_per_day': 10,
                'max_campaign_pauses_per_day': 5,
                'max_daily_budget_increase_percent': Decimal('50'),
                'max_daily_budget_decrease_percent': Decimal('30'),
                'is_enabled': True,
            }
        )
        accounts_with_limits.append({
            'account': account,
            'safety_limit': safety_limit
        })

    # Calculate global statistics
    total_accounts = len(accounts_with_limits)
    enabled_accounts = sum(1 for item in accounts_with_limits if item['safety_limit'].is_enabled)
    total_max_bid_changes = sum(item['safety_limit'].max_bid_changes_per_day for item in accounts_with_limits)
    total_max_budget_changes = sum(item['safety_limit'].max_budget_changes_per_day for item in accounts_with_limits)

    context = {
        'accounts_with_limits': accounts_with_limits,
        'total_accounts': total_accounts,
        'enabled_accounts': enabled_accounts,
        'total_max_bid_changes': total_max_bid_changes,
        'total_max_budget_changes': total_max_budget_changes,
    }

    return render(request, 'core/autopilot_safety_controls.html', context)


@login_required
def advertising_overview(request):
    """
    Advertising overview page showing campaign summary, quick stats, and performance overview.
    """
    from apps.accounts.models import Organization
    from apps.amazon_auth.models import AmazonAccount
    from apps.amazon_ads.models import Campaign, AdGroup, Keyword, CampaignPerformance
    from django.db.models import Sum, Count, Avg, Q
    from datetime import datetime, timedelta
    from decimal import Decimal
    
    # Get user's organizations
    user_organizations = Organization.objects.filter(
        Q(owner=request.user) | Q(members=request.user)
    ).distinct()
    
    # Get connected Amazon accounts for user's organizations
    amazon_accounts = AmazonAccount.objects.filter(
        organization__in=user_organizations,
        is_connected=True
    )
    
    # Get campaigns for connected accounts
    campaigns = Campaign.objects.filter(account__in=amazon_accounts)
    
    # Get date range (last 30 days)
    today = datetime.now().date()
    last_30_days = today - timedelta(days=30)
    last_7_days = today - timedelta(days=7)
    
    # Get performance data
    performance_data = CampaignPerformance.objects.filter(
        campaign__in=campaigns,
        date__gte=last_30_days
    )
    
    # Calculate summary stats
    total_campaigns = campaigns.count()
    active_campaigns = campaigns.filter(state='enabled').count()
    paused_campaigns = campaigns.filter(state='paused').count()
    archived_campaigns = campaigns.filter(state='archived').count()
    
    # Get ad groups
    ad_groups = AdGroup.objects.filter(campaign__in=campaigns)
    total_ad_groups = ad_groups.count()
    
    # Get keywords
    keywords = Keyword.objects.filter(ad_group__in=ad_groups)
    total_keywords = keywords.count()
    
    # Calculate spend and sales
    total_spend = performance_data.aggregate(total=Sum('cost'))['total'] or Decimal('0.00')
    total_sales = performance_data.aggregate(total=Sum('sales'))['total'] or Decimal('0.00')
    total_orders = performance_data.aggregate(total=Sum('orders'))['total'] or 0
    
    # Calculate average ACOS
    if total_sales > 0:
        avg_acos = (float(total_spend) / float(total_sales)) * 100
    else:
        avg_acos = 0
    
    # Get campaigns with budgets
    campaigns_with_budget = campaigns.exclude(daily_budget__isnull=True).exclude(daily_budget=0)
    total_budgets = campaigns_with_budget.count()
    
    # Calculate daily spend trend (last 7 days)
    daily_spend = {}
    max_daily_spend = Decimal('0.00')
    for i in range(7):
        date = today - timedelta(days=i)
        day_spend = performance_data.filter(date=date).aggregate(total=Sum('cost'))['total'] or Decimal('0.00')
        daily_spend[date.isoformat()] = float(day_spend)
        if day_spend > max_daily_spend:
            max_daily_spend = day_spend
    
    # Get campaigns by type
    campaigns_by_type = campaigns.values('campaign_type').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Get top performing campaigns (by sales, last 30 days)
    top_campaigns = campaigns.annotate(
        total_sales=Sum('performance_data__sales', filter=Q(performance_data__date__gte=last_30_days)),
        total_spend=Sum('performance_data__cost', filter=Q(performance_data__date__gte=last_30_days)),
        total_orders=Sum('performance_data__orders', filter=Q(performance_data__date__gte=last_30_days))
    ).filter(
        total_sales__gt=0
    ).order_by('-total_sales')[:5]
    
    # Calculate ACOS for top campaigns
    for campaign in top_campaigns:
        if campaign.total_sales and campaign.total_sales > 0:
            campaign.calculated_acos = (float(campaign.total_spend or 0) / float(campaign.total_sales)) * 100
        else:
            campaign.calculated_acos = 0
    
    # Get campaigns needing attention (high ACOS or low performance)
    campaigns_needing_attention = []
    for campaign in campaigns.annotate(
        total_sales=Sum('performance_data__sales', filter=Q(performance_data__date__gte=last_30_days)),
        total_spend=Sum('performance_data__cost', filter=Q(performance_data__date__gte=last_30_days))
    ).filter(
        total_sales__gt=0,
        state='enabled'
    ):
        campaign_acos = (float(campaign.total_spend or 0) / float(campaign.total_sales)) * 100
        if campaign_acos > 50:  # ACOS above 50%
            campaigns_needing_attention.append({
                'campaign': campaign,
                'acos': campaign_acos,
                'issue': 'High ACOS',
                'spend': float(campaign.total_spend or 0),
                'sales': float(campaign.total_sales)
            })
    
    # Sort by ACOS descending
    campaigns_needing_attention.sort(key=lambda x: x['acos'], reverse=True)
    campaigns_needing_attention = campaigns_needing_attention[:5]
    
    # Get recent campaign changes (using updated_at)
    recent_campaigns = campaigns.order_by('-updated_at')[:5]
    
    # Budget alerts (campaigns spending close to or over budget)
    budget_alerts = []
    for campaign in campaigns_with_budget.filter(state='enabled'):
        if campaign.daily_budget:
            # Calculate average daily spend (last 7 days)
            avg_daily_spend = performance_data.filter(
                campaign=campaign,
                date__gte=last_7_days
            ).aggregate(avg=Avg('cost'))['avg'] or Decimal('0.00')
            
            if avg_daily_spend > campaign.daily_budget * Decimal('0.9'):  # Spending 90%+ of budget
                budget_alerts.append({
                    'campaign': campaign,
                    'daily_budget': float(campaign.daily_budget),
                    'avg_daily_spend': float(avg_daily_spend),
                    'utilization': (float(avg_daily_spend) / float(campaign.daily_budget)) * 100
                })
    
    # Sort by utilization descending
    budget_alerts.sort(key=lambda x: x['utilization'], reverse=True)
    budget_alerts = budget_alerts[:5]
    
    context = {
        'total_campaigns': total_campaigns,
        'active_campaigns': active_campaigns,
        'paused_campaigns': paused_campaigns,
        'archived_campaigns': archived_campaigns,
        'total_ad_groups': total_ad_groups,
        'total_keywords': total_keywords,
        'total_spend': float(total_spend),
        'total_sales': float(total_sales),
        'total_orders': total_orders,
        'avg_acos': avg_acos,
        'total_budgets': total_budgets,
        'daily_spend': daily_spend,
        'max_daily_spend': float(max_daily_spend),
        'campaigns_by_type': campaigns_by_type,
        'top_campaigns': top_campaigns,
        'campaigns_needing_attention': campaigns_needing_attention,
        'recent_campaigns': recent_campaigns,
        'budget_alerts': budget_alerts,
        'date_range': {
            'start': last_30_days,
            'end': today
        }
    }
    
    return render(request, 'core/advertising.html', context)


@login_required
def campaigns_list(request):
    """
    Campaign management page with list, filters, search, and CRUD operations.
    """
    from apps.accounts.models import Organization
    from apps.amazon_auth.models import AmazonAccount
    from apps.amazon_ads.models import Campaign, CampaignPerformance
    from django.db.models import Sum, Q, Count
    from django.shortcuts import redirect, get_object_or_404
    from django.contrib import messages
    from datetime import datetime, timedelta
    from decimal import Decimal
    
    # Get user's organizations
    user_organizations = Organization.objects.filter(
        Q(owner=request.user) | Q(members=request.user)
    ).distinct()
    
    # Get connected Amazon accounts
    amazon_accounts = AmazonAccount.objects.filter(
        organization__in=user_organizations,
        is_connected=True
    )
    
    # Get all campaigns
    campaigns = Campaign.objects.filter(account__in=amazon_accounts)
    
    # Handle POST requests (Create, Update, Pause/Resume, Bulk Actions)
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create':
            # Create new campaign
            try:
                account_id = request.POST.get('account')
                account = get_object_or_404(AmazonAccount, id=account_id, organization__in=user_organizations)
                
                campaign = Campaign.objects.create(
                    account=account,
                    campaign_id=f"TEMP_{datetime.now().timestamp()}",  # Temporary ID, will be replaced by API
                    name=request.POST.get('name'),
                    campaign_type=request.POST.get('campaign_type', 'sponsored_products'),
                    state=request.POST.get('state', 'enabled'),
                    daily_budget=request.POST.get('daily_budget') or None,
                    bidding_strategy=request.POST.get('bidding_strategy', 'manual'),
                    targeting_type=request.POST.get('targeting_type', ''),
                    start_date=request.POST.get('start_date') or None,
                    end_date=request.POST.get('end_date') or None,
                )
                messages.success(request, f'Campaign "{campaign.name}" created successfully.')
            except Exception as e:
                messages.error(request, f'Error creating campaign: {str(e)}')
        
        elif action == 'update':
            # Update existing campaign
            try:
                campaign_id = request.POST.get('campaign_id')
                campaign = get_object_or_404(Campaign, id=campaign_id, account__organization__in=user_organizations)
                
                campaign.name = request.POST.get('name', campaign.name)
                campaign.campaign_type = request.POST.get('campaign_type', campaign.campaign_type)
                campaign.state = request.POST.get('state', campaign.state)
                campaign.daily_budget = request.POST.get('daily_budget') or None
                campaign.bidding_strategy = request.POST.get('bidding_strategy', campaign.bidding_strategy)
                campaign.targeting_type = request.POST.get('targeting_type', campaign.targeting_type)
                campaign.start_date = request.POST.get('start_date') or None
                campaign.end_date = request.POST.get('end_date') or None
                campaign.save()
                
                messages.success(request, f'Campaign "{campaign.name}" updated successfully.')
            except Exception as e:
                messages.error(request, f'Error updating campaign: {str(e)}')
        
        elif action == 'pause':
            # Pause campaign
            try:
                campaign_id = request.POST.get('campaign_id')
                campaign = get_object_or_404(Campaign, id=campaign_id, account__organization__in=user_organizations)
                campaign.state = 'paused'
                campaign.save()
                messages.success(request, f'Campaign "{campaign.name}" paused successfully.')
            except Exception as e:
                messages.error(request, f'Error pausing campaign: {str(e)}')
        
        elif action == 'resume':
            # Resume campaign
            try:
                campaign_id = request.POST.get('campaign_id')
                campaign = get_object_or_404(Campaign, id=campaign_id, account__organization__in=user_organizations)
                campaign.state = 'enabled'
                campaign.save()
                messages.success(request, f'Campaign "{campaign.name}" resumed successfully.')
            except Exception as e:
                messages.error(request, f'Error resuming campaign: {str(e)}')
        
        elif action == 'bulk_pause':
            # Bulk pause campaigns
            try:
                campaign_ids = request.POST.getlist('campaign_ids')
                updated = Campaign.objects.filter(
                    id__in=campaign_ids,
                    account__organization__in=user_organizations
                ).update(state='paused')
                messages.success(request, f'{updated} campaign(s) paused successfully.')
            except Exception as e:
                messages.error(request, f'Error pausing campaigns: {str(e)}')
        
        elif action == 'bulk_resume':
            # Bulk resume campaigns
            try:
                campaign_ids = request.POST.getlist('campaign_ids')
                updated = Campaign.objects.filter(
                    id__in=campaign_ids,
                    account__organization__in=user_organizations
                ).update(state='enabled')
                messages.success(request, f'{updated} campaign(s) resumed successfully.')
            except Exception as e:
                messages.error(request, f'Error resuming campaigns: {str(e)}')
        
        elif action == 'bulk_delete':
            # Bulk delete campaigns
            try:
                campaign_ids = request.POST.getlist('campaign_ids')
                deleted = Campaign.objects.filter(
                    id__in=campaign_ids,
                    account__organization__in=user_organizations
                ).delete()[0]
                messages.success(request, f'{deleted} campaign(s) deleted successfully.')
            except Exception as e:
                messages.error(request, f'Error deleting campaigns: {str(e)}')
        
        return redirect('campaigns_list')
    
    # Handle GET requests (List with filters and search)
    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        campaigns = campaigns.filter(
            Q(name__icontains=search_query) |
            Q(campaign_id__icontains=search_query)
        )
    
    # Filters
    state_filter = request.GET.get('state', '')
    if state_filter:
        campaigns = campaigns.filter(state=state_filter)
    
    type_filter = request.GET.get('type', '')
    if type_filter:
        campaigns = campaigns.filter(campaign_type=type_filter)
    
    account_filter = request.GET.get('account', '')
    if account_filter:
        campaigns = campaigns.filter(account_id=account_filter)
    
    # Get date range for performance (last 30 days)
    today = datetime.now().date()
    last_30_days = today - timedelta(days=30)
    
    # Annotate campaigns with performance data
    campaigns = campaigns.annotate(
        total_spend=Sum('performance_data__cost', filter=Q(performance_data__date__gte=last_30_days)),
        total_sales=Sum('performance_data__sales', filter=Q(performance_data__date__gte=last_30_days)),
        total_orders=Sum('performance_data__orders', filter=Q(performance_data__date__gte=last_30_days)),
        total_clicks=Sum('performance_data__clicks', filter=Q(performance_data__date__gte=last_30_days)),
        total_impressions=Sum('performance_data__impressions', filter=Q(performance_data__date__gte=last_30_days)),
    )
    
    # Calculate ACOS for each campaign
    for campaign in campaigns:
        if campaign.total_sales and campaign.total_sales > 0:
            campaign.calculated_acos = (float(campaign.total_spend or 0) / float(campaign.total_sales)) * 100
        else:
            campaign.calculated_acos = 0
        
        if campaign.total_clicks and campaign.total_clicks > 0:
            campaign.calculated_ctr = (float(campaign.total_clicks or 0) / float(campaign.total_impressions or 1)) * 100
        else:
            campaign.calculated_ctr = 0
    
    # Order by updated_at descending
    campaigns = campaigns.order_by('-updated_at')
    
    # Counts for filters
    total_count = Campaign.objects.filter(account__in=amazon_accounts).count()
    enabled_count = Campaign.objects.filter(account__in=amazon_accounts, state='enabled').count()
    paused_count = Campaign.objects.filter(account__in=amazon_accounts, state='paused').count()
    archived_count = Campaign.objects.filter(account__in=amazon_accounts, state='archived').count()
    
    context = {
        'campaigns': campaigns,
        'amazon_accounts': amazon_accounts,
        'search_query': search_query,
        'state_filter': state_filter,
        'type_filter': type_filter,
        'account_filter': account_filter,
        'total_count': total_count,
        'enabled_count': enabled_count,
        'paused_count': paused_count,
        'archived_count': archived_count,
        'campaign_types': Campaign.CAMPAIGN_TYPE_CHOICES,
        'campaign_states': Campaign.STATE_CHOICES,
        'bidding_strategies': Campaign.BIDDING_STRATEGY_CHOICES,
    }
    
    return render(request, 'core/campaigns_list.html', context)


@login_required
def sponsored_products_list(request):
    """
    Sponsored Products management page for managing Sponsored Products campaigns specifically.
    Features: Campaign list, product targeting, bid management, performance metrics.
    """
    from apps.accounts.models import Organization
    from apps.amazon_auth.models import AmazonAccount
    from apps.amazon_ads.models import Campaign, AdGroup, Keyword, CampaignPerformance
    from apps.amazon_sp.models import Product
    from django.db.models import Sum, Q, Count, Avg
    from django.shortcuts import redirect, get_object_or_404
    from django.contrib import messages
    from datetime import datetime, timedelta
    from decimal import Decimal
    
    # Get user's organizations
    user_organizations = Organization.objects.filter(
        Q(owner=request.user) | Q(members=request.user)
    ).distinct()
    
    # Get connected Amazon accounts
    amazon_accounts = AmazonAccount.objects.filter(
        organization__in=user_organizations,
        is_connected=True
    )
    
    # Get only Sponsored Products campaigns
    campaigns = Campaign.objects.filter(
        account__in=amazon_accounts,
        campaign_type='sponsored_products'
    )
    
    # Handle POST requests (Bid updates, Product targeting)
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_bid':
            # Update keyword bid
            try:
                keyword_id = request.POST.get('keyword_id')
                new_bid = request.POST.get('bid')
                keyword = get_object_or_404(
                    Keyword,
                    id=keyword_id,
                    ad_group__campaign__account__organization__in=user_organizations,
                    ad_group__campaign__campaign_type='sponsored_products'
                )
                keyword.bid = Decimal(new_bid)
                keyword.save()
                messages.success(request, f'Bid updated successfully for keyword "{keyword.keyword_text}".')
            except Exception as e:
                messages.error(request, f'Error updating bid: {str(e)}')
        
        elif action == 'bulk_update_bids':
            # Bulk update keyword bids
            try:
                keyword_ids = request.POST.getlist('keyword_ids')
                bid_change_type = request.POST.get('bid_change_type')  # 'absolute' or 'percentage'
                bid_value = Decimal(request.POST.get('bid_value', 0))
                
                updated = 0
                for keyword_id in keyword_ids:
                    keyword = Keyword.objects.filter(
                        id=keyword_id,
                        ad_group__campaign__account__organization__in=user_organizations,
                        ad_group__campaign__campaign_type='sponsored_products'
                    ).first()
                    if keyword:
                        if bid_change_type == 'absolute':
                            keyword.bid = bid_value
                        elif bid_change_type == 'percentage' and keyword.bid:
                            keyword.bid = keyword.bid * (1 + bid_value / 100)
                        keyword.save()
                        updated += 1
                
                messages.success(request, f'{updated} keyword bid(s) updated successfully.')
            except Exception as e:
                messages.error(request, f'Error updating bids: {str(e)}')
        
        return redirect('sponsored_products_list')
    
    # Handle GET requests (List with filters and search)
    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        campaigns = campaigns.filter(
            Q(name__icontains=search_query) |
            Q(campaign_id__icontains=search_query)
        )
    
    # Filters
    state_filter = request.GET.get('state', '')
    if state_filter:
        campaigns = campaigns.filter(state=state_filter)
    
    account_filter = request.GET.get('account', '')
    if account_filter:
        campaigns = campaigns.filter(account_id=account_filter)
    
    # Get date range for performance (last 30 days)
    today = datetime.now().date()
    last_30_days = today - timedelta(days=30)
    
    # Annotate campaigns with performance data
    campaigns = campaigns.annotate(
        total_spend=Sum('performance_data__cost', filter=Q(performance_data__date__gte=last_30_days)),
        total_sales=Sum('performance_data__sales', filter=Q(performance_data__date__gte=last_30_days)),
        total_orders=Sum('performance_data__orders', filter=Q(performance_data__date__gte=last_30_days)),
        total_clicks=Sum('performance_data__clicks', filter=Q(performance_data__date__gte=last_30_days)),
        total_impressions=Sum('performance_data__impressions', filter=Q(performance_data__date__gte=last_30_days)),
        ad_groups_count=Count('ad_groups', distinct=True),
        keywords_count=Count('ad_groups__keywords', distinct=True),
    )
    
    # Calculate metrics for each campaign
    for campaign in campaigns:
        if campaign.total_sales and campaign.total_sales > 0:
            campaign.calculated_acos = (float(campaign.total_spend or 0) / float(campaign.total_sales)) * 100
        else:
            campaign.calculated_acos = 0
        
        if campaign.total_clicks and campaign.total_impressions and campaign.total_impressions > 0:
            campaign.calculated_ctr = (float(campaign.total_clicks or 0) / float(campaign.total_impressions)) * 100
        else:
            campaign.calculated_ctr = 0
        
        if campaign.total_clicks and campaign.total_clicks > 0:
            campaign.calculated_cvr = (float(campaign.total_orders or 0) / float(campaign.total_clicks)) * 100
        else:
            campaign.calculated_cvr = 0
        
        # Calculate average bid for this campaign
        avg_bid = keywords.filter(ad_group__campaign=campaign).aggregate(avg=Avg('bid'))['avg']
        campaign.avg_bid = avg_bid or None
    
    # Get ad groups and keywords for product targeting section
    ad_groups = AdGroup.objects.filter(campaign__in=campaigns)
    keywords = Keyword.objects.filter(ad_group__in=ad_groups)
    
    # Get products from SP-API (if available)
    products = Product.objects.filter(account__in=amazon_accounts)
    
    # Get top performing keywords for bid management section
    top_keywords = keywords.annotate(
        total_spend=Sum('performance_data__cost', filter=Q(performance_data__date__gte=last_30_days)),
        total_sales=Sum('performance_data__sales', filter=Q(performance_data__date__gte=last_30_days)),
        total_clicks=Sum('performance_data__clicks', filter=Q(performance_data__date__gte=last_30_days)),
    ).filter(
        total_spend__gt=0
    ).order_by('-total_spend')[:20]
    
    # Calculate ACOS for keywords
    for keyword in top_keywords:
        if keyword.total_sales and keyword.total_sales > 0:
            keyword.calculated_acos = (float(keyword.total_spend or 0) / float(keyword.total_sales)) * 100
        else:
            keyword.calculated_acos = 0
    
    # Get average bid by campaign (convert to list for template)
    campaign_bids_list = []
    for campaign in campaigns:
        avg_bid = keywords.filter(ad_group__campaign=campaign).aggregate(avg=Avg('bid'))['avg']
        campaign_bids_list.append({
            'campaign_id': campaign.id,
            'avg_bid': avg_bid or Decimal('0.00')
        })
    
    # Counts for filters
    total_count = Campaign.objects.filter(
        account__in=amazon_accounts,
        campaign_type='sponsored_products'
    ).count()
    enabled_count = Campaign.objects.filter(
        account__in=amazon_accounts,
        campaign_type='sponsored_products',
        state='enabled'
    ).count()
    paused_count = Campaign.objects.filter(
        account__in=amazon_accounts,
        campaign_type='sponsored_products',
        state='paused'
    ).count()
    
    # Calculate account-level performance summaries
    account_summaries = []
    for account in amazon_accounts:
        account_campaigns = [c for c in campaigns if c.account.id == account.id]
        if account_campaigns:
            total_spend = sum(float(c.total_spend or 0) for c in account_campaigns)
            total_sales = sum(float(c.total_sales or 0) for c in account_campaigns)
            account_summaries.append({
                'account': account,
                'campaign_count': len(account_campaigns),
                'total_spend': total_spend,
                'total_sales': total_sales
            })
    
    context = {
        'campaigns': campaigns,
        'amazon_accounts': amazon_accounts,
        'ad_groups': ad_groups,
        'keywords': keywords,
        'top_keywords': top_keywords,
        'products': products,
        'campaign_bids_list': campaign_bids_list,
        'account_summaries': account_summaries,
        'search_query': search_query,
        'state_filter': state_filter,
        'account_filter': account_filter,
        'total_count': total_count,
        'enabled_count': enabled_count,
        'paused_count': paused_count,
        'campaign_states': Campaign.STATE_CHOICES,
        'date_range': {
            'start': last_30_days,
            'end': today
        }
    }
    
    return render(request, 'core/sponsored_products_list.html', context)


@login_required
def ad_groups_list(request):
    """
    Ad Group management page for organizing campaigns into ad groups.
    Features: Ad group list, Create/Edit ad groups, Ad group performance, Keywords per ad group.
    """
    from apps.accounts.models import Organization
    from apps.amazon_auth.models import AmazonAccount
    from apps.amazon_ads.models import Campaign, AdGroup, Keyword, KeywordPerformance
    from django.db.models import Sum, Q, Count, Avg
    from django.shortcuts import redirect, get_object_or_404
    from django.contrib import messages
    from datetime import datetime, timedelta
    from decimal import Decimal
    
    # Get user's organizations
    user_organizations = Organization.objects.filter(
        Q(owner=request.user) | Q(members=request.user)
    ).distinct()
    
    # Get connected Amazon accounts
    amazon_accounts = AmazonAccount.objects.filter(
        organization__in=user_organizations,
        is_connected=True
    )
    
    # Get all campaigns
    campaigns = Campaign.objects.filter(account__in=amazon_accounts)
    
    # Get all ad groups
    ad_groups = AdGroup.objects.filter(campaign__in=campaigns)
    
    # Handle POST requests (Create, Update, Pause/Resume)
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create':
            # Create new ad group
            try:
                campaign_id = request.POST.get('campaign')
                campaign = get_object_or_404(Campaign, id=campaign_id, account__organization__in=user_organizations)
                
                ad_group = AdGroup.objects.create(
                    campaign=campaign,
                    ad_group_id=f"TEMP_{datetime.now().timestamp()}",  # Temporary ID, will be replaced by API
                    name=request.POST.get('name'),
                    state=request.POST.get('state', 'enabled'),
                    default_bid=request.POST.get('default_bid') or None,
                )
                messages.success(request, f'Ad Group "{ad_group.name}" created successfully.')
            except Exception as e:
                messages.error(request, f'Error creating ad group: {str(e)}')
        
        elif action == 'update':
            # Update existing ad group
            try:
                ad_group_id = request.POST.get('ad_group_id')
                ad_group = get_object_or_404(AdGroup, id=ad_group_id, campaign__account__organization__in=user_organizations)
                
                ad_group.name = request.POST.get('name', ad_group.name)
                ad_group.state = request.POST.get('state', ad_group.state)
                ad_group.default_bid = request.POST.get('default_bid') or None
                ad_group.campaign = get_object_or_404(Campaign, id=request.POST.get('campaign'), account__organization__in=user_organizations)
                ad_group.save()
                
                messages.success(request, f'Ad Group "{ad_group.name}" updated successfully.')
            except Exception as e:
                messages.error(request, f'Error updating ad group: {str(e)}')
        
        elif action == 'pause':
            # Pause ad group
            try:
                ad_group_id = request.POST.get('ad_group_id')
                ad_group = get_object_or_404(AdGroup, id=ad_group_id, campaign__account__organization__in=user_organizations)
                ad_group.state = 'paused'
                ad_group.save()
                messages.success(request, f'Ad Group "{ad_group.name}" paused successfully.')
            except Exception as e:
                messages.error(request, f'Error pausing ad group: {str(e)}')
        
        elif action == 'resume':
            # Resume ad group
            try:
                ad_group_id = request.POST.get('ad_group_id')
                ad_group = get_object_or_404(AdGroup, id=ad_group_id, campaign__account__organization__in=user_organizations)
                ad_group.state = 'enabled'
                ad_group.save()
                messages.success(request, f'Ad Group "{ad_group.name}" resumed successfully.')
            except Exception as e:
                messages.error(request, f'Error resuming ad group: {str(e)}')
        
        return redirect('ad_groups_list')
    
    # Handle GET requests (List with filters and search)
    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        ad_groups = ad_groups.filter(
            Q(name__icontains=search_query) |
            Q(ad_group_id__icontains=search_query) |
            Q(campaign__name__icontains=search_query)
        )
    
    # Filters
    state_filter = request.GET.get('state', '')
    if state_filter:
        ad_groups = ad_groups.filter(state=state_filter)
    
    campaign_filter = request.GET.get('campaign', '')
    if campaign_filter:
        ad_groups = ad_groups.filter(campaign_id=campaign_filter)
    
    account_filter = request.GET.get('account', '')
    if account_filter:
        ad_groups = ad_groups.filter(campaign__account_id=account_filter)
    
    # Get date range for performance (last 30 days)
    today = datetime.now().date()
    last_30_days = today - timedelta(days=30)
    
    # Annotate ad groups with keyword counts and performance data
    ad_groups = ad_groups.annotate(
        keywords_count=Count('keywords', distinct=True),
        total_spend=Sum('keywords__performance_data__cost', filter=Q(keywords__performance_data__date__gte=last_30_days)),
        total_sales=Sum('keywords__performance_data__sales', filter=Q(keywords__performance_data__date__gte=last_30_days)),
        total_orders=Sum('keywords__performance_data__orders', filter=Q(keywords__performance_data__date__gte=last_30_days)),
        total_clicks=Sum('keywords__performance_data__clicks', filter=Q(keywords__performance_data__date__gte=last_30_days)),
        total_impressions=Sum('keywords__performance_data__impressions', filter=Q(keywords__performance_data__date__gte=last_30_days)),
    )
    
    # Calculate metrics for each ad group
    for ad_group in ad_groups:
        if ad_group.total_sales and ad_group.total_sales > 0:
            ad_group.calculated_acos = (float(ad_group.total_spend or 0) / float(ad_group.total_sales)) * 100
        else:
            ad_group.calculated_acos = 0
        
        if ad_group.total_clicks and ad_group.total_impressions and ad_group.total_impressions > 0:
            ad_group.calculated_ctr = (float(ad_group.total_clicks or 0) / float(ad_group.total_impressions)) * 100
        else:
            ad_group.calculated_ctr = 0
        
        if ad_group.total_clicks and ad_group.total_clicks > 0:
            ad_group.calculated_cvr = (float(ad_group.total_orders or 0) / float(ad_group.total_clicks)) * 100
        else:
            ad_group.calculated_cvr = 0
    
    # Order by updated_at descending
    ad_groups = ad_groups.order_by('-updated_at')
    
    # Counts for filters
    total_count = AdGroup.objects.filter(campaign__in=campaigns).count()
    enabled_count = AdGroup.objects.filter(campaign__in=campaigns, state='enabled').count()
    paused_count = AdGroup.objects.filter(campaign__in=campaigns, state='paused').count()
    
    context = {
        'ad_groups': ad_groups,
        'campaigns': campaigns,
        'amazon_accounts': amazon_accounts,
        'search_query': search_query,
        'state_filter': state_filter,
        'campaign_filter': campaign_filter,
        'account_filter': account_filter,
        'total_count': total_count,
        'enabled_count': enabled_count,
        'paused_count': paused_count,
        'ad_group_states': AdGroup.STATE_CHOICES,
        'date_range': {
            'start': last_30_days,
            'end': today
        }
    }
    
    return render(request, 'core/ad_groups_list.html', context)


@login_required
def keywords_list(request):
    """
    Keywords management page for managing keywords across campaigns.
    Features: Keyword list with filters, Add/Remove keywords, Bid management, Keyword performance metrics, Search term analysis.
    """
    from apps.accounts.models import Organization
    from apps.amazon_auth.models import AmazonAccount
    from apps.amazon_ads.models import Campaign, AdGroup, Keyword, KeywordPerformance, SearchTerm
    from django.db.models import Sum, Q, Count, Avg
    from django.shortcuts import redirect, get_object_or_404
    from django.contrib import messages
    from datetime import datetime, timedelta
    from decimal import Decimal
    
    # Get user's organizations
    user_organizations = Organization.objects.filter(
        Q(owner=request.user) | Q(members=request.user)
    ).distinct()
    
    # Get connected Amazon accounts
    amazon_accounts = AmazonAccount.objects.filter(
        organization__in=user_organizations,
        is_connected=True
    )
    
    # Get all campaigns
    campaigns = Campaign.objects.filter(account__in=amazon_accounts)
    
    # Get all ad groups
    ad_groups = AdGroup.objects.filter(campaign__in=campaigns)
    
    # Get all keywords
    keywords = Keyword.objects.filter(ad_group__in=ad_groups)
    
    # Handle POST requests (Create, Update, Delete, Pause/Resume, Bid Updates)
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create':
            # Create new keyword
            try:
                ad_group_id = request.POST.get('ad_group')
                ad_group = get_object_or_404(AdGroup, id=ad_group_id, campaign__account__organization__in=user_organizations)
                
                keyword = Keyword.objects.create(
                    ad_group=ad_group,
                    keyword_id=f"TEMP_{datetime.now().timestamp()}",  # Temporary ID, will be replaced by API
                    keyword_text=request.POST.get('keyword_text'),
                    match_type=request.POST.get('match_type', 'broad'),
                    state=request.POST.get('state', 'enabled'),
                    bid=request.POST.get('bid') or None,
                )
                messages.success(request, f'Keyword "{keyword.keyword_text}" created successfully.')
            except Exception as e:
                messages.error(request, f'Error creating keyword: {str(e)}')
        
        elif action == 'update':
            # Update existing keyword
            try:
                keyword_id = request.POST.get('keyword_id')
                keyword = get_object_or_404(Keyword, id=keyword_id, ad_group__campaign__account__organization__in=user_organizations)
                
                keyword.keyword_text = request.POST.get('keyword_text', keyword.keyword_text)
                keyword.match_type = request.POST.get('match_type', keyword.match_type)
                keyword.state = request.POST.get('state', keyword.state)
                keyword.bid = request.POST.get('bid') or None
                keyword.ad_group = get_object_or_404(AdGroup, id=request.POST.get('ad_group'), campaign__account__organization__in=user_organizations)
                keyword.save()
                
                messages.success(request, f'Keyword "{keyword.keyword_text}" updated successfully.')
            except Exception as e:
                messages.error(request, f'Error updating keyword: {str(e)}')
        
        elif action == 'delete':
            # Delete keyword
            try:
                keyword_id = request.POST.get('keyword_id')
                keyword = get_object_or_404(Keyword, id=keyword_id, ad_group__campaign__account__organization__in=user_organizations)
                keyword_text = keyword.keyword_text
                keyword.delete()
                messages.success(request, f'Keyword "{keyword_text}" deleted successfully.')
            except Exception as e:
                messages.error(request, f'Error deleting keyword: {str(e)}')
        
        elif action == 'pause':
            # Pause keyword
            try:
                keyword_id = request.POST.get('keyword_id')
                keyword = get_object_or_404(Keyword, id=keyword_id, ad_group__campaign__account__organization__in=user_organizations)
                keyword.state = 'paused'
                keyword.save()
                messages.success(request, f'Keyword "{keyword.keyword_text}" paused successfully.')
            except Exception as e:
                messages.error(request, f'Error pausing keyword: {str(e)}')
        
        elif action == 'resume':
            # Resume keyword
            try:
                keyword_id = request.POST.get('keyword_id')
                keyword = get_object_or_404(Keyword, id=keyword_id, ad_group__campaign__account__organization__in=user_organizations)
                keyword.state = 'enabled'
                keyword.save()
                messages.success(request, f'Keyword "{keyword.keyword_text}" resumed successfully.')
            except Exception as e:
                messages.error(request, f'Error resuming keyword: {str(e)}')
        
        elif action == 'update_bid':
            # Update keyword bid
            try:
                keyword_id = request.POST.get('keyword_id')
                new_bid = request.POST.get('bid')
                keyword = get_object_or_404(Keyword, id=keyword_id, ad_group__campaign__account__organization__in=user_organizations)
                keyword.bid = Decimal(new_bid) if new_bid else None
                keyword.save()
                messages.success(request, f'Bid updated successfully for keyword "{keyword.keyword_text}".')
            except Exception as e:
                messages.error(request, f'Error updating bid: {str(e)}')
        
        elif action == 'bulk_update_bids':
            # Bulk update keyword bids
            try:
                keyword_ids = request.POST.getlist('keyword_ids')
                bid_change_type = request.POST.get('bid_change_type')  # 'absolute' or 'percentage'
                bid_value = Decimal(request.POST.get('bid_value', 0))
                
                updated = 0
                for keyword_id in keyword_ids:
                    keyword = Keyword.objects.filter(
                        id=keyword_id,
                        ad_group__campaign__account__organization__in=user_organizations
                    ).first()
                    if keyword:
                        if bid_change_type == 'absolute':
                            keyword.bid = (keyword.bid or Decimal('0.00')) + bid_value
                        elif bid_change_type == 'percentage':
                            keyword.bid = (keyword.bid or Decimal('0.00')) * (1 + bid_value / 100)
                        keyword.save()
                        updated += 1
                
                messages.success(request, f'{updated} keyword bid(s) updated successfully.')
            except Exception as e:
                messages.error(request, f'Error updating bids: {str(e)}')
        
        elif action == 'bulk_delete':
            # Bulk delete keywords
            try:
                keyword_ids = request.POST.getlist('keyword_ids')
                deleted = Keyword.objects.filter(
                    id__in=keyword_ids,
                    ad_group__campaign__account__organization__in=user_organizations
                ).delete()[0]
                messages.success(request, f'{deleted} keyword(s) deleted successfully.')
            except Exception as e:
                messages.error(request, f'Error deleting keywords: {str(e)}')
        
        return redirect('keywords_list')
    
    # Handle GET requests (List with filters and search)
    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        keywords = keywords.filter(
            Q(keyword_text__icontains=search_query) |
            Q(keyword_id__icontains=search_query) |
            Q(ad_group__name__icontains=search_query) |
            Q(ad_group__campaign__name__icontains=search_query)
        )
    
    # Filters
    state_filter = request.GET.get('state', '')
    if state_filter:
        keywords = keywords.filter(state=state_filter)
    
    match_type_filter = request.GET.get('match_type', '')
    if match_type_filter:
        keywords = keywords.filter(match_type=match_type_filter)
    
    campaign_filter = request.GET.get('campaign', '')
    if campaign_filter:
        keywords = keywords.filter(ad_group__campaign_id=campaign_filter)
    
    ad_group_filter = request.GET.get('ad_group', '')
    if ad_group_filter:
        keywords = keywords.filter(ad_group_id=ad_group_filter)
    
    account_filter = request.GET.get('account', '')
    if account_filter:
        keywords = keywords.filter(ad_group__campaign__account_id=account_filter)
    
    # Get date range for performance (last 30 days)
    today = datetime.now().date()
    last_30_days = today - timedelta(days=30)
    
    # Annotate keywords with performance data
    keywords = keywords.annotate(
        total_spend=Sum('performance_data__cost', filter=Q(performance_data__date__gte=last_30_days)),
        total_sales=Sum('performance_data__sales', filter=Q(performance_data__date__gte=last_30_days)),
        total_orders=Sum('performance_data__orders', filter=Q(performance_data__date__gte=last_30_days)),
        total_clicks=Sum('performance_data__clicks', filter=Q(performance_data__date__gte=last_30_days)),
        total_impressions=Sum('performance_data__impressions', filter=Q(performance_data__date__gte=last_30_days)),
    )
    
    # Calculate metrics for each keyword
    for keyword in keywords:
        if keyword.total_sales and keyword.total_sales > 0:
            keyword.calculated_acos = (float(keyword.total_spend or 0) / float(keyword.total_sales)) * 100
        else:
            keyword.calculated_acos = 0
        
        if keyword.total_clicks and keyword.total_impressions and keyword.total_impressions > 0:
            keyword.calculated_ctr = (float(keyword.total_clicks or 0) / float(keyword.total_impressions)) * 100
        else:
            keyword.calculated_ctr = 0
        
        if keyword.total_clicks and keyword.total_clicks > 0:
            keyword.calculated_cvr = (float(keyword.total_orders or 0) / float(keyword.total_clicks)) * 100
        else:
            keyword.calculated_cvr = 0
        
        if keyword.total_clicks and keyword.total_clicks > 0:
            keyword.calculated_cpc = float(keyword.total_spend or 0) / float(keyword.total_clicks)
        else:
            keyword.calculated_cpc = 0
    
    # Order by updated_at descending
    keywords = keywords.order_by('-updated_at')
    
    # Get search terms for analysis (top search terms by cost, last 30 days)
    search_terms = SearchTerm.objects.filter(
        keyword__in=keywords,
        date__gte=last_30_days
    ).values('query').annotate(
        total_cost=Sum('cost'),
        total_sales=Sum('sales'),
        total_clicks=Sum('clicks'),
        total_impressions=Sum('impressions'),
        total_orders=Sum('orders'),
    ).order_by('-total_cost')[:20]
    
    # Calculate ACOS for search terms
    for term in search_terms:
        if term['total_sales'] and term['total_sales'] > 0:
            term['acos'] = (float(term['total_cost'] or 0) / float(term['total_sales'])) * 100
        else:
            term['acos'] = 0
    
    # Counts for filters
    total_count = Keyword.objects.filter(ad_group__in=ad_groups).count()
    enabled_count = Keyword.objects.filter(ad_group__in=ad_groups, state='enabled').count()
    paused_count = Keyword.objects.filter(ad_group__in=ad_groups, state='paused').count()
    archived_count = Keyword.objects.filter(ad_group__in=ad_groups, state='archived').count()
    
    context = {
        'keywords': keywords,
        'campaigns': campaigns,
        'ad_groups': ad_groups,
        'amazon_accounts': amazon_accounts,
        'search_terms': search_terms,
        'search_query': search_query,
        'state_filter': state_filter,
        'match_type_filter': match_type_filter,
        'campaign_filter': campaign_filter,
        'ad_group_filter': ad_group_filter,
        'account_filter': account_filter,
        'total_count': total_count,
        'enabled_count': enabled_count,
        'paused_count': paused_count,
        'archived_count': archived_count,
        'keyword_states': Keyword.STATE_CHOICES,
        'match_types': Keyword.MATCH_TYPE_CHOICES,
        'date_range': {
            'start': last_30_days,
            'end': today
        }
    }
    
    return render(request, 'core/keywords_list.html', context)


@login_required
def search_terms_list(request):
    """
    Search terms analysis page showing actual search terms that triggered ads.
    Features: Search terms report, Performance analysis, Add to keywords, Add to negative keywords, Filtering and sorting.
    """
    from apps.accounts.models import Organization
    from apps.amazon_auth.models import AmazonAccount
    from apps.amazon_ads.models import Campaign, AdGroup, Keyword, SearchTerm, NegativeKeyword
    from django.db.models import Sum, Q, Count, Avg, Min, Max, Min, Max
    from django.shortcuts import redirect, get_object_or_404
    from django.contrib import messages
    from datetime import datetime, timedelta
    from decimal import Decimal
    
    # Get user's organizations
    user_organizations = Organization.objects.filter(
        Q(owner=request.user) | Q(members=request.user)
    ).distinct()
    
    # Get connected Amazon accounts
    amazon_accounts = AmazonAccount.objects.filter(
        organization__in=user_organizations,
        is_connected=True
    )
    
    # Get all campaigns
    campaigns = Campaign.objects.filter(account__in=amazon_accounts)
    
    # Get all ad groups
    ad_groups = AdGroup.objects.filter(campaign__in=campaigns)
    
    # Get all search terms
    search_terms = SearchTerm.objects.filter(campaign__in=campaigns)
    
    # Handle POST requests (Add to keywords, Add to negative keywords)
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add_to_keywords':
            # Add search term as a new keyword
            try:
                search_term_id = request.POST.get('search_term_id')
                search_term = get_object_or_404(SearchTerm, id=search_term_id, campaign__account__organization__in=user_organizations)
                ad_group_id = request.POST.get('ad_group')
                match_type = request.POST.get('match_type', 'broad')
                bid = request.POST.get('bid') or None
                
                ad_group = get_object_or_404(AdGroup, id=ad_group_id, campaign__account__organization__in=user_organizations)
                
                # Check if keyword already exists
                existing_keyword = Keyword.objects.filter(
                    ad_group=ad_group,
                    keyword_text=search_term.query
                ).first()
                
                if existing_keyword:
                    messages.warning(request, f'Keyword "{search_term.query}" already exists in this ad group.')
                else:
                    keyword = Keyword.objects.create(
                        ad_group=ad_group,
                        keyword_id=f"TEMP_{datetime.now().timestamp()}",
                        keyword_text=search_term.query,
                        match_type=match_type,
                        state='enabled',
                        bid=Decimal(bid) if bid else None,
                    )
                    messages.success(request, f'Search term "{search_term.query}" added as keyword successfully.')
            except Exception as e:
                messages.error(request, f'Error adding search term to keywords: {str(e)}')
        
        elif action == 'add_to_negative_keywords':
            # Add search term as a negative keyword
            try:
                search_term_id = request.POST.get('search_term_id')
                search_term = get_object_or_404(SearchTerm, id=search_term_id, campaign__account__organization__in=user_organizations)
                match_type = request.POST.get('match_type', 'negativeExact')
                target_type = request.POST.get('target_type')  # 'campaign' or 'ad_group'
                target_id = request.POST.get('target_id')
                
                if target_type == 'campaign':
                    campaign = get_object_or_404(Campaign, id=target_id, account__organization__in=user_organizations)
                    # Check if negative keyword already exists
                    existing = NegativeKeyword.objects.filter(
                        campaign=campaign,
                        keyword_text=search_term.query
                    ).first()
                    
                    if existing:
                        messages.warning(request, f'Negative keyword "{search_term.query}" already exists for this campaign.')
                    else:
                        negative_keyword = NegativeKeyword.objects.create(
                            campaign=campaign,
                            keyword_id=f"TEMP_{datetime.now().timestamp()}",
                            keyword_text=search_term.query,
                            match_type=match_type,
                            state='enabled',
                        )
                        messages.success(request, f'Search term "{search_term.query}" added as negative keyword to campaign successfully.')
                elif target_type == 'ad_group':
                    ad_group = get_object_or_404(AdGroup, id=target_id, campaign__account__organization__in=user_organizations)
                    # Check if negative keyword already exists
                    existing = NegativeKeyword.objects.filter(
                        ad_group=ad_group,
                        keyword_text=search_term.query
                    ).first()
                    
                    if existing:
                        messages.warning(request, f'Negative keyword "{search_term.query}" already exists for this ad group.')
                    else:
                        negative_keyword = NegativeKeyword.objects.create(
                            ad_group=ad_group,
                            keyword_id=f"TEMP_{datetime.now().timestamp()}",
                            keyword_text=search_term.query,
                            match_type=match_type,
                            state='enabled',
                        )
                        messages.success(request, f'Search term "{search_term.query}" added as negative keyword to ad group successfully.')
            except Exception as e:
                messages.error(request, f'Error adding search term to negative keywords: {str(e)}')
        
        return redirect('search_terms_list')
    
    # Handle GET requests (List with filters and sorting)
    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        search_terms = search_terms.filter(query__icontains=search_query)
    
    # Filters
    campaign_filter = request.GET.get('campaign', '')
    if campaign_filter:
        search_terms = search_terms.filter(campaign_id=campaign_filter)
    
    ad_group_filter = request.GET.get('ad_group', '')
    if ad_group_filter:
        search_terms = search_terms.filter(ad_group_id=ad_group_filter)
    
    account_filter = request.GET.get('account', '')
    if account_filter:
        search_terms = search_terms.filter(campaign__account_id=account_filter)
    
    # Date range filter
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            search_terms = search_terms.filter(date__gte=date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            search_terms = search_terms.filter(date__lte=date_to_obj)
        except ValueError:
            pass
    
    # If no date filter, default to last 30 days
    if not date_from and not date_to:
        today = datetime.now().date()
        last_30_days = today - timedelta(days=30)
        search_terms = search_terms.filter(date__gte=last_30_days)
    
    # Sorting
    sort_by = request.GET.get('sort_by', '-cost')
    valid_sort_fields = ['-cost', 'cost', '-sales', 'sales', '-clicks', 'clicks', '-impressions', 'impressions', '-acos', 'acos', '-roas', 'roas', '-date', 'date', 'query', '-query']
    if sort_by in valid_sort_fields:
        search_terms = search_terms.order_by(sort_by)
    else:
        search_terms = search_terms.order_by('-date', '-cost')
    
    # Aggregate search terms by query (group duplicates)
    # First, get the first ID for each unique query/campaign/ad_group combination
    search_terms_aggregated = []
    for term_group in search_terms.values('query', 'campaign', 'ad_group', 'campaign__name', 'ad_group__name', 'campaign__account__account_name').distinct():
        group_terms = search_terms.filter(
            query=term_group['query'],
            campaign_id=term_group['campaign'],
            ad_group_id=term_group['ad_group']
        )
        
        aggregated = group_terms.aggregate(
            total_impressions=Sum('impressions'),
            total_clicks=Sum('clicks'),
            total_cost=Sum('cost'),
            total_sales=Sum('sales'),
            total_orders=Sum('orders'),
            date_range_min=Min('date'),
            date_range_max=Max('date'),
        )
        
        # Get the first search term ID for this group
        first_term = group_terms.first()
        aggregated['query'] = term_group['query']
        aggregated['campaign'] = term_group['campaign']
        aggregated['ad_group'] = term_group['ad_group']
        aggregated['campaign__name'] = term_group['campaign__name']
        aggregated['ad_group__name'] = term_group['ad_group__name']
        aggregated['campaign__account__account_name'] = term_group['campaign__account__account_name']
        aggregated['first_search_term_id'] = first_term.id if first_term else None
        
        # Calculate metrics for sorting
        if aggregated['total_sales'] and aggregated['total_sales'] > 0:
            aggregated['calculated_acos'] = (float(aggregated['total_cost'] or 0) / float(aggregated['total_sales'])) * 100
            aggregated['calculated_roas'] = float(aggregated['total_sales'] or 0) / float(aggregated['total_cost'] or 1)
        else:
            aggregated['calculated_acos'] = 0
            aggregated['calculated_roas'] = 0
        
        # Calculate CTR and CPC
        if aggregated['total_clicks'] and aggregated['total_clicks'] > 0:
            aggregated['calculated_ctr'] = (float(aggregated['total_clicks'] or 0) / float(aggregated['total_impressions'] or 1)) * 100
            aggregated['calculated_cpc'] = float(aggregated['total_cost'] or 0) / float(aggregated['total_clicks'])
        else:
            aggregated['calculated_ctr'] = 0
            aggregated['calculated_cpc'] = 0
        
        search_terms_aggregated.append(aggregated)
    
    # Apply sorting
    reverse_order = sort_by.startswith('-')
    sort_field = sort_by.lstrip('-')
    
    if sort_field == 'cost':
        search_terms_aggregated = sorted(search_terms_aggregated, key=lambda x: float(x['total_cost'] or 0), reverse=reverse_order)
    elif sort_field == 'sales':
        search_terms_aggregated = sorted(search_terms_aggregated, key=lambda x: float(x['total_sales'] or 0), reverse=reverse_order)
    elif sort_field == 'clicks':
        search_terms_aggregated = sorted(search_terms_aggregated, key=lambda x: int(x['total_clicks'] or 0), reverse=reverse_order)
    elif sort_field == 'impressions':
        search_terms_aggregated = sorted(search_terms_aggregated, key=lambda x: int(x['total_impressions'] or 0), reverse=reverse_order)
    elif sort_field == 'acos':
        search_terms_aggregated = sorted(search_terms_aggregated, key=lambda x: x.get('calculated_acos', 0), reverse=reverse_order)
    elif sort_field == 'roas':
        search_terms_aggregated = sorted(search_terms_aggregated, key=lambda x: x.get('calculated_roas', 0), reverse=reverse_order)
    elif sort_field == 'date':
        search_terms_aggregated = sorted(search_terms_aggregated, key=lambda x: x.get('date_range_max', ''), reverse=reverse_order)
    elif sort_field == 'query':
        search_terms_aggregated = sorted(search_terms_aggregated, key=lambda x: x['query'].lower(), reverse=reverse_order)
    else:
        # Default: sort by total_cost descending
        search_terms_aggregated = sorted(search_terms_aggregated, key=lambda x: float(x['total_cost'] or 0), reverse=True)
    
    # Get individual search term records for detailed view (if needed)
    search_terms_list = list(search_terms.select_related('campaign', 'ad_group', 'keyword', 'campaign__account')[:1000])
    
    # Calculate summary stats
    total_search_terms = search_terms.count()
    unique_queries = search_terms.values('query').distinct().count()
    
    summary_stats = search_terms.aggregate(
        total_impressions=Sum('impressions'),
        total_clicks=Sum('clicks'),
        total_cost=Sum('cost'),
        total_sales=Sum('sales'),
        total_orders=Sum('orders'),
    )
    
    if summary_stats['total_sales'] and summary_stats['total_sales'] > 0:
        overall_acos = (float(summary_stats['total_cost'] or 0) / float(summary_stats['total_sales'])) * 100
        overall_roas = float(summary_stats['total_sales'] or 0) / float(summary_stats['total_cost'] or 1)
    else:
        overall_acos = 0
        overall_roas = 0
    
    context = {
        'search_terms_aggregated': search_terms_aggregated,
        'search_terms_list': search_terms_list,
        'campaigns': campaigns,
        'ad_groups': ad_groups,
        'amazon_accounts': amazon_accounts,
        'search_query': search_query,
        'campaign_filter': campaign_filter,
        'ad_group_filter': ad_group_filter,
        'account_filter': account_filter,
        'date_from': date_from,
        'date_to': date_to,
        'sort_by': sort_by,
        'total_search_terms': total_search_terms,
        'unique_queries': unique_queries,
        'summary_stats': summary_stats,
        'overall_acos': overall_acos,
        'overall_roas': overall_roas,
        'match_types': Keyword.MATCH_TYPE_CHOICES,
        'negative_match_types': NegativeKeyword.MATCH_TYPE_CHOICES,
        'date_range': {
            'start': date_from or (datetime.now().date() - timedelta(days=30)).isoformat(),
            'end': date_to or datetime.now().date().isoformat()
        }
    }
    
    return render(request, 'core/search_terms_list.html', context)


@login_required
def negative_keywords_list(request):
    """
    Negative keywords management page for excluding unwanted search terms.
    Features: Negative keyword list, Add/Remove negative keywords, Campaign/Ad group level negative keywords, Bulk import/export.
    """
    from apps.accounts.models import Organization
    from apps.amazon_auth.models import AmazonAccount
    from apps.amazon_ads.models import Campaign, AdGroup, NegativeKeyword
    from django.db.models import Q
    from django.shortcuts import redirect, get_object_or_404
    from django.contrib import messages
    from django.http import HttpResponse
    from datetime import datetime
    import csv
    import io
    
    # Get user's organizations
    user_organizations = Organization.objects.filter(
        Q(owner=request.user) | Q(members=request.user)
    ).distinct()
    
    # Get connected Amazon accounts
    amazon_accounts = AmazonAccount.objects.filter(
        organization__in=user_organizations,
        is_connected=True
    )
    
    # Get all campaigns
    campaigns = Campaign.objects.filter(account__in=amazon_accounts)
    
    # Get all ad groups
    ad_groups = AdGroup.objects.filter(campaign__in=campaigns)
    
    # Get all negative keywords
    negative_keywords = NegativeKeyword.objects.filter(
        Q(campaign__in=campaigns) | Q(ad_group__in=ad_groups)
    ).select_related('campaign', 'ad_group', 'campaign__account')
    
    # Handle POST requests (Create, Update, Delete, Bulk Import)
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create':
            # Create new negative keyword
            try:
                target_type = request.POST.get('target_type')  # 'campaign' or 'ad_group'
                target_id = request.POST.get('target_id')
                keyword_text = request.POST.get('keyword_text').strip()
                match_type = request.POST.get('match_type', 'negativeExact')
                state = request.POST.get('state', 'enabled')
                
                if target_type == 'campaign':
                    campaign = get_object_or_404(Campaign, id=target_id, account__organization__in=user_organizations)
                    # Check if negative keyword already exists
                    existing = NegativeKeyword.objects.filter(
                        campaign=campaign,
                        keyword_text=keyword_text
                    ).first()
                    
                    if existing:
                        messages.warning(request, f'Negative keyword "{keyword_text}" already exists for this campaign.')
                    else:
                        negative_keyword = NegativeKeyword.objects.create(
                            campaign=campaign,
                            keyword_id=f"TEMP_{datetime.now().timestamp()}",
                            keyword_text=keyword_text,
                            match_type=match_type,
                            state=state,
                        )
                        messages.success(request, f'Negative keyword "{keyword_text}" added successfully.')
                elif target_type == 'ad_group':
                    ad_group = get_object_or_404(AdGroup, id=target_id, campaign__account__organization__in=user_organizations)
                    # Check if negative keyword already exists
                    existing = NegativeKeyword.objects.filter(
                        ad_group=ad_group,
                        keyword_text=keyword_text
                    ).first()
                    
                    if existing:
                        messages.warning(request, f'Negative keyword "{keyword_text}" already exists for this ad group.')
                    else:
                        negative_keyword = NegativeKeyword.objects.create(
                            ad_group=ad_group,
                            keyword_id=f"TEMP_{datetime.now().timestamp()}",
                            keyword_text=keyword_text,
                            match_type=match_type,
                            state=state,
                        )
                        messages.success(request, f'Negative keyword "{keyword_text}" added successfully.')
            except Exception as e:
                messages.error(request, f'Error creating negative keyword: {str(e)}')
        
        elif action == 'update':
            # Update existing negative keyword
            try:
                negative_keyword_id = request.POST.get('negative_keyword_id')
                negative_keyword = get_object_or_404(
                    NegativeKeyword.objects.filter(
                        Q(campaign__account__organization__in=user_organizations) | Q(ad_group__campaign__account__organization__in=user_organizations)
                    ),
                    id=negative_keyword_id
                )
                
                negative_keyword.keyword_text = request.POST.get('keyword_text', negative_keyword.keyword_text).strip()
                negative_keyword.match_type = request.POST.get('match_type', negative_keyword.match_type)
                negative_keyword.state = request.POST.get('state', negative_keyword.state)
                
                # Update target if changed
                target_type = request.POST.get('target_type')
                target_id = request.POST.get('target_id')
                if target_type == 'campaign':
                    campaign = get_object_or_404(Campaign, id=target_id, account__organization__in=user_organizations)
                    negative_keyword.campaign = campaign
                    negative_keyword.ad_group = None
                elif target_type == 'ad_group':
                    ad_group = get_object_or_404(AdGroup, id=target_id, campaign__account__organization__in=user_organizations)
                    negative_keyword.ad_group = ad_group
                    negative_keyword.campaign = None
                
                negative_keyword.save()
                messages.success(request, f'Negative keyword "{negative_keyword.keyword_text}" updated successfully.')
            except Exception as e:
                messages.error(request, f'Error updating negative keyword: {str(e)}')
        
        elif action == 'delete':
            # Delete negative keyword
            try:
                negative_keyword_id = request.POST.get('negative_keyword_id')
                negative_keyword = get_object_or_404(
                    NegativeKeyword.objects.filter(
                        Q(campaign__account__organization__in=user_organizations) | Q(ad_group__campaign__account__organization__in=user_organizations)
                    ),
                    id=negative_keyword_id
                )
                keyword_text = negative_keyword.keyword_text
                negative_keyword.delete()
                messages.success(request, f'Negative keyword "{keyword_text}" deleted successfully.')
            except Exception as e:
                messages.error(request, f'Error deleting negative keyword: {str(e)}')
        
        elif action == 'bulk_delete':
            # Bulk delete negative keywords
            try:
                negative_keyword_ids = request.POST.getlist('negative_keyword_ids')
                deleted = NegativeKeyword.objects.filter(
                    Q(id__in=negative_keyword_ids) &
                    (Q(campaign__account__organization__in=user_organizations) | Q(ad_group__campaign__account__organization__in=user_organizations))
                ).delete()[0]
                messages.success(request, f'{deleted} negative keyword(s) deleted successfully.')
            except Exception as e:
                messages.error(request, f'Error deleting negative keywords: {str(e)}')
        
        elif action == 'bulk_import':
            # Bulk import from CSV
            try:
                csv_file = request.FILES.get('csv_file')
                if not csv_file:
                    messages.error(request, 'No CSV file provided.')
                    return redirect('negative_keywords_list')
                
                # Read CSV file
                decoded_file = csv_file.read().decode('utf-8')
                io_string = io.StringIO(decoded_file)
                reader = csv.DictReader(io_string)
                
                imported_count = 0
                skipped_count = 0
                errors = []
                
                for row in reader:
                    try:
                        keyword_text = row.get('keyword_text', '').strip()
                        match_type = row.get('match_type', 'negativeExact').strip()
                        state = row.get('state', 'enabled').strip()
                        target_type = row.get('target_type', '').strip()  # 'campaign' or 'ad_group'
                        target_id = row.get('target_id', '').strip()
                        
                        if not keyword_text:
                            skipped_count += 1
                            continue
                        
                        if target_type == 'campaign' and target_id:
                            campaign = Campaign.objects.filter(
                                id=target_id,
                                account__organization__in=user_organizations
                            ).first()
                            if campaign:
                                existing = NegativeKeyword.objects.filter(
                                    campaign=campaign,
                                    keyword_text=keyword_text
                                ).first()
                                if not existing:
                                    NegativeKeyword.objects.create(
                                        campaign=campaign,
                                        keyword_id=f"TEMP_{datetime.now().timestamp()}_{imported_count}",
                                        keyword_text=keyword_text,
                                        match_type=match_type,
                                        state=state,
                                    )
                                    imported_count += 1
                                else:
                                    skipped_count += 1
                            else:
                                skipped_count += 1
                        elif target_type == 'ad_group' and target_id:
                            ad_group = AdGroup.objects.filter(
                                id=target_id,
                                campaign__account__organization__in=user_organizations
                            ).first()
                            if ad_group:
                                existing = NegativeKeyword.objects.filter(
                                    ad_group=ad_group,
                                    keyword_text=keyword_text
                                ).first()
                                if not existing:
                                    NegativeKeyword.objects.create(
                                        ad_group=ad_group,
                                        keyword_id=f"TEMP_{datetime.now().timestamp()}_{imported_count}",
                                        keyword_text=keyword_text,
                                        match_type=match_type,
                                        state=state,
                                    )
                                    imported_count += 1
                                else:
                                    skipped_count += 1
                            else:
                                skipped_count += 1
                        else:
                            skipped_count += 1
                    except Exception as e:
                        errors.append(f"Row error: {str(e)}")
                        skipped_count += 1
                
                if imported_count > 0:
                    messages.success(request, f'{imported_count} negative keyword(s) imported successfully.')
                if skipped_count > 0:
                    messages.warning(request, f'{skipped_count} row(s) skipped (duplicates or invalid data).')
                if errors:
                    messages.error(request, f'Some errors occurred during import: {", ".join(errors[:5])}')
            except Exception as e:
                messages.error(request, f'Error importing CSV: {str(e)}')
        
        return redirect('negative_keywords_list')
    
    # Handle GET requests (List with filters, Export)
    export_format = request.GET.get('export', '')
    if export_format == 'csv':
        # Export to CSV
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="negative_keywords_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['keyword_text', 'match_type', 'state', 'target_type', 'target_id', 'target_name', 'account_name'])
        
        for nk in negative_keywords:
            if nk.campaign:
                target_type = 'campaign'
                target_id = nk.campaign.id
                target_name = nk.campaign.name
                account_name = nk.campaign.account.account_name
            else:
                target_type = 'ad_group'
                target_id = nk.ad_group.id
                target_name = nk.ad_group.name
                account_name = nk.ad_group.campaign.account.account_name
            
            writer.writerow([
                nk.keyword_text,
                nk.match_type,
                nk.state,
                target_type,
                target_id,
                target_name,
                account_name
            ])
        
        return response
    
    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        negative_keywords = negative_keywords.filter(keyword_text__icontains=search_query)
    
    # Filters
    match_type_filter = request.GET.get('match_type', '')
    if match_type_filter:
        negative_keywords = negative_keywords.filter(match_type=match_type_filter)
    
    state_filter = request.GET.get('state', '')
    if state_filter:
        negative_keywords = negative_keywords.filter(state=state_filter)
    
    target_type_filter = request.GET.get('target_type', '')
    if target_type_filter == 'campaign':
        negative_keywords = negative_keywords.exclude(campaign__isnull=True)
    elif target_type_filter == 'ad_group':
        negative_keywords = negative_keywords.exclude(ad_group__isnull=True)
    
    campaign_filter = request.GET.get('campaign', '')
    if campaign_filter:
        negative_keywords = negative_keywords.filter(campaign_id=campaign_filter)
    
    ad_group_filter = request.GET.get('ad_group', '')
    if ad_group_filter:
        negative_keywords = negative_keywords.filter(ad_group_id=ad_group_filter)
    
    account_filter = request.GET.get('account', '')
    if account_filter:
        negative_keywords = negative_keywords.filter(
            Q(campaign__account_id=account_filter) | Q(ad_group__campaign__account_id=account_filter)
        )
    
    # Order by created_at descending
    negative_keywords = negative_keywords.order_by('-created_at')
    
    # Counts for filters
    total_count = NegativeKeyword.objects.filter(
        Q(campaign__in=campaigns) | Q(ad_group__in=ad_groups)
    ).count()
    enabled_count = NegativeKeyword.objects.filter(
        Q(campaign__in=campaigns) | Q(ad_group__in=ad_groups),
        state='enabled'
    ).count()
    paused_count = NegativeKeyword.objects.filter(
        Q(campaign__in=campaigns) | Q(ad_group__in=ad_groups),
        state='paused'
    ).count()
    campaign_level_count = NegativeKeyword.objects.filter(
        Q(campaign__in=campaigns) | Q(ad_group__in=ad_groups),
        campaign__isnull=False
    ).count()
    ad_group_level_count = NegativeKeyword.objects.filter(
        Q(campaign__in=campaigns) | Q(ad_group__in=ad_groups),
        ad_group__isnull=False
    ).count()
    
    context = {
        'negative_keywords': negative_keywords,
        'campaigns': campaigns,
        'ad_groups': ad_groups,
        'amazon_accounts': amazon_accounts,
        'search_query': search_query,
        'match_type_filter': match_type_filter,
        'state_filter': state_filter,
        'target_type_filter': target_type_filter,
        'campaign_filter': campaign_filter,
        'ad_group_filter': ad_group_filter,
        'account_filter': account_filter,
        'total_count': total_count,
        'enabled_count': enabled_count,
        'paused_count': paused_count,
        'campaign_level_count': campaign_level_count,
        'ad_group_level_count': ad_group_level_count,
        'match_types': NegativeKeyword.MATCH_TYPE_CHOICES,
        'states': NegativeKeyword.STATE_CHOICES,
    }
    
    return render(request, 'core/negative_keywords_list.html', context)


@login_required
def budgets_list(request):
    """
    Budget management page for setting and monitoring campaign budgets.
    Features: Budget list, Create/Edit budgets, Budget utilization tracking, Budget alerts, Daily/Monthly budget limits.
    """
    from apps.accounts.models import Organization
    from apps.amazon_auth.models import AmazonAccount
    from apps.amazon_ads.models import Campaign, CampaignPerformance
    from django.db.models import Sum, Q, Count
    from django.shortcuts import redirect, get_object_or_404
    from django.contrib import messages
    from datetime import datetime, timedelta
    from decimal import Decimal
    
    # Get user's organizations
    user_organizations = Organization.objects.filter(
        Q(owner=request.user) | Q(members=request.user)
    ).distinct()
    
    # Get connected Amazon accounts
    amazon_accounts = AmazonAccount.objects.filter(
        organization__in=user_organizations,
        is_connected=True
    )
    
    # Get all campaigns
    campaigns = Campaign.objects.filter(account__in=amazon_accounts)
    
    # Handle POST requests (Create/Edit budgets)
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_budget':
            # Update campaign budget
            try:
                campaign_id = request.POST.get('campaign_id')
                daily_budget = request.POST.get('daily_budget')
                monthly_budget_limit = request.POST.get('monthly_budget_limit')  # Optional
                
                campaign = get_object_or_404(Campaign, id=campaign_id, account__organization__in=user_organizations)
                
                if daily_budget:
                    campaign.daily_budget = Decimal(daily_budget)
                else:
                    campaign.daily_budget = None
                
                campaign.save()
                messages.success(request, f'Budget updated successfully for campaign "{campaign.name}".')
            except Exception as e:
                messages.error(request, f'Error updating budget: {str(e)}')
        
        return redirect('budgets_list')
    
    # Get date ranges
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    last_7_days = today - timedelta(days=7)
    last_30_days = today - timedelta(days=30)
    current_month_start = today.replace(day=1)
    
    # Get performance data
    performance_data = CampaignPerformance.objects.filter(
        campaign__in=campaigns,
        date__gte=last_30_days
    )
    
    # Annotate campaigns with budget utilization data
    campaigns = campaigns.annotate(
        daily_spend=Sum('performance_data__cost', filter=Q(performance_data__date=yesterday)),
        weekly_spend=Sum('performance_data__cost', filter=Q(performance_data__date__gte=last_7_days)),
        monthly_spend=Sum('performance_data__cost', filter=Q(performance_data__date__gte=last_30_days)),
        current_month_spend=Sum('performance_data__cost', filter=Q(performance_data__date__gte=current_month_start)),
    )
    
    # Calculate budget metrics for each campaign
    budget_list = []
    total_daily_budget = Decimal('0.00')
    total_monthly_budget = Decimal('0.00')
    total_daily_spend = Decimal('0.00')
    total_monthly_spend = Decimal('0.00')
    alerts_count = 0
    
    for campaign in campaigns:
        daily_budget = campaign.daily_budget or Decimal('0.00')
        daily_spend = campaign.daily_spend or Decimal('0.00')
        monthly_spend = campaign.monthly_spend or Decimal('0.00')
        
        # Calculate monthly budget (daily_budget * 30)
        monthly_budget = daily_budget * 30 if daily_budget > 0 else Decimal('0.00')
        
        # Calculate utilization
        daily_utilization = (daily_spend / daily_budget * 100) if daily_budget > 0 else 0
        monthly_utilization = (monthly_spend / monthly_budget * 100) if monthly_budget > 0 else 0
        
        # Projected monthly spend (based on current month's average daily spend)
        days_in_month = today.day
        if days_in_month > 0:
            avg_daily_spend = campaign.current_month_spend / days_in_month if campaign.current_month_spend else Decimal('0.00')
            projected_monthly_spend = avg_daily_spend * 30
        else:
            projected_monthly_spend = Decimal('0.00')
        
        # Budget alerts
        alerts = []
        alert_level = 'none'
        
        if daily_budget > 0:
            if daily_utilization >= 100:
                alerts.append('Daily budget exceeded')
                alert_level = 'error'
            elif daily_utilization >= 90:
                alerts.append('Daily budget at 90%+')
                alert_level = 'warning'
            elif daily_utilization >= 80:
                alerts.append('Daily budget at 80%+')
                alert_level = 'info'
        
        if monthly_budget > 0:
            if monthly_utilization >= 100:
                alerts.append('Monthly budget exceeded')
                alert_level = 'error'
            elif monthly_utilization >= 90:
                alerts.append('Monthly budget at 90%+')
                alert_level = 'warning'
            elif monthly_utilization >= 80:
                alerts.append('Monthly budget at 80%+')
                alert_level = 'info'
        
        if projected_monthly_spend > monthly_budget and monthly_budget > 0:
            alerts.append('Projected to exceed monthly budget')
            if alert_level == 'none':
                alert_level = 'warning'
        
        if alert_level != 'none':
            alerts_count += 1
        
        # Remaining budget
        daily_remaining = daily_budget - daily_spend if daily_budget > 0 else Decimal('0.00')
        monthly_remaining = monthly_budget - monthly_spend if monthly_budget > 0 else Decimal('0.00')
        
        budget_list.append({
            'campaign': campaign,
            'daily_budget': daily_budget,
            'monthly_budget': monthly_budget,
            'daily_spend': daily_spend,
            'weekly_spend': campaign.weekly_spend or Decimal('0.00'),
            'monthly_spend': monthly_spend,
            'current_month_spend': campaign.current_month_spend or Decimal('0.00'),
            'projected_monthly_spend': projected_monthly_spend,
            'daily_utilization': daily_utilization,
            'monthly_utilization': monthly_utilization,
            'daily_remaining': daily_remaining,
            'monthly_remaining': monthly_remaining,
            'alerts': alerts,
            'alert_level': alert_level,
        })
        
        total_daily_budget += daily_budget
        total_monthly_budget += monthly_budget
        total_daily_spend += daily_spend
        total_monthly_spend += monthly_spend
    
    # Calculate overall utilization
    overall_daily_utilization = (total_daily_spend / total_daily_budget * 100) if total_daily_budget > 0 else 0
    overall_monthly_utilization = (total_monthly_spend / total_monthly_budget * 100) if total_monthly_budget > 0 else 0
    
    # Filters
    search_query = request.GET.get('search', '')
    if search_query:
        budget_list = [b for b in budget_list if search_query.lower() in b['campaign'].name.lower()]
    
    account_filter = request.GET.get('account', '')
    if account_filter:
        budget_list = [b for b in budget_list if b['campaign'].account.id == int(account_filter)]
    
    alert_filter = request.GET.get('alert', '')
    if alert_filter:
        if alert_filter == 'has_alerts':
            budget_list = [b for b in budget_list if b['alert_level'] != 'none']
        elif alert_filter == 'no_alerts':
            budget_list = [b for b in budget_list if b['alert_level'] == 'none']
    
    # Sort by utilization (highest first) or by campaign name
    sort_by = request.GET.get('sort_by', 'utilization')
    if sort_by == 'utilization':
        budget_list = sorted(budget_list, key=lambda x: max(x['daily_utilization'], x['monthly_utilization']), reverse=True)
    elif sort_by == 'campaign':
        budget_list = sorted(budget_list, key=lambda x: x['campaign'].name)
    elif sort_by == 'budget':
        budget_list = sorted(budget_list, key=lambda x: x['daily_budget'], reverse=True)
    
    context = {
        'budget_list': budget_list,
        'campaigns': campaigns,
        'amazon_accounts': amazon_accounts,
        'search_query': search_query,
        'account_filter': account_filter,
        'alert_filter': alert_filter,
        'sort_by': sort_by,
        'total_daily_budget': total_daily_budget,
        'total_monthly_budget': total_monthly_budget,
        'total_daily_spend': total_daily_spend,
        'total_monthly_spend': total_monthly_spend,
        'overall_daily_utilization': overall_daily_utilization,
        'overall_monthly_utilization': overall_monthly_utilization,
        'alerts_count': alerts_count,
        'total_campaigns': len(budget_list),
        'campaigns_with_budget': len([b for b in budget_list if b['daily_budget'] > 0]),
        'date_range': {
            'yesterday': yesterday,
            'last_7_days': last_7_days,
            'last_30_days': last_30_days,
            'current_month_start': current_month_start,
        }
    }
    
    return render(request, 'core/budgets_list.html', context)


def register_view(request):
    """
    Web-based user registration view.
    """
    if request.user.is_authenticated:
        return redirect('/dashboard/')
    
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')
        
        # Validation
        errors = []
        if not first_name:
            errors.append('First name is required.')
        if not last_name:
            errors.append('Last name is required.')
        if not email:
            errors.append('Email is required.')
        elif User.objects.filter(email=email).exists():
            errors.append('An account with this email already exists.')
        if not password:
            errors.append('Password is required.')
        elif len(password) < 8:
            errors.append('Password must be at least 8 characters long.')
        if password != password_confirm:
            errors.append('Passwords do not match.')
        
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            try:
                # Create user
                user = User.objects.create_user(
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name
                )
                messages.success(request, 'Account created successfully! Please log in.')
                return redirect('/login/')
            except Exception as e:
                messages.error(request, f'Error creating account: {str(e)}')
    
    return render(request, 'core/register.html')


def logout_view(request):
    """
    Web-based logout view.
    """
    # Clear all existing messages before logging out
    list(messages.get_messages(request))  # Consume all existing messages
    
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('/login/')


def password_reset_view(request):
    """
    Password reset view - allows users to change password or request password reset via email.
    """
    if request.user.is_authenticated:
        return redirect('/dashboard/')
    
    return render(request, 'core/password_reset.html')


def password_change_view(request):
    """
    Handle password change with current password verification.
    """
    if request.user.is_authenticated:
        return redirect('/dashboard/')
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        current_password = request.POST.get('current_password', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')
        
        # Validation
        errors = []
        if not email:
            errors.append('Email is required.')
        if not current_password:
            errors.append('Current password is required.')
        if not new_password:
            errors.append('New password is required.')
        elif len(new_password) < 8:
            errors.append('New password must be at least 8 characters long.')
        if new_password != confirm_password:
            errors.append('New passwords do not match.')
        
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            try:
                user = User.objects.get(email=email)
                # Verify current password
                if user.check_password(current_password):
                    user.set_password(new_password)
                    user.save()
                    messages.success(request, 'Password changed successfully! You can now log in with your new password.')
                    return redirect('/login/')
                else:
                    messages.error(request, 'Current password is incorrect.')
            except User.DoesNotExist:
                messages.error(request, 'No account found with this email address.')
            except Exception as e:
                messages.error(request, f'Error changing password: {str(e)}')
    
    return redirect('/password-reset/')


def forgot_password_view(request):
    """
    Handle forgot password - generate new password and send via email.
    """
    if request.user.is_authenticated:
        return redirect('/dashboard/')
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        
        if not email:
            messages.error(request, 'Email is required.')
        else:
            try:
                user = User.objects.get(email=email)
                
                # Generate a random password
                alphabet = string.ascii_letters + string.digits + string.punctuation
                new_password = ''.join(secrets.choice(alphabet) for i in range(12))
                
                # Set the new password
                user.set_password(new_password)
                user.save()
                
                # Send email with new password
                try:
                    send_mail(
                        subject='Appca - Your New Password',
                        message=f'Your new password is: {new_password}\n\nPlease log in and change it to something more memorable.',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[email],
                        fail_silently=False,
                    )
                    messages.success(request, 'A new password has been sent to your email address.')
                except Exception as e:
                    messages.error(request, f'Error sending email: {str(e)}. Please contact support.')
                
            except User.DoesNotExist:
                messages.error(request, 'No account found with this email address.')
            except Exception as e:
                messages.error(request, f'Error processing request: {str(e)}')
    
    return redirect('/password-reset/')


@login_required
def settings_view(request):
    """
    Settings/Profile page - allows users to update their profile information.
    """
    if request.method == 'POST':
        # Handle profile update
        if 'update_profile' in request.POST:
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            birthday = request.POST.get('birthday', '').strip()
            profile_picture = request.FILES.get('profile_picture')
            
            # Validation
            errors = []
            if not first_name:
                errors.append('First name is required.')
            if not last_name:
                errors.append('Last name is required.')
            
            if errors:
                for error in errors:
                    messages.error(request, error)
            else:
                try:
                    user = request.user
                    user.first_name = first_name
                    user.last_name = last_name
                    
                    if birthday:
                        from datetime import datetime
                        try:
                            user.birthday = datetime.strptime(birthday, '%Y-%m-%d').date()
                        except ValueError:
                            messages.error(request, 'Invalid date format.')
                            return render(request, 'core/settings.html', {'user': user})
                    
                    if profile_picture:
                        # Delete old profile picture if exists
                        if user.profile_picture:
                            try:
                                import os
                                from django.conf import settings
                                old_path = user.profile_picture.path
                                if os.path.isfile(old_path):
                                    os.remove(old_path)
                            except Exception:
                                pass  # Ignore errors when deleting old file
                        user.profile_picture = profile_picture
                    
                    user.save()
                    messages.success(request, 'Profile updated successfully!')
                    # Redirect to prevent resubmission and refresh the page
                    return redirect('/settings/')
                except Exception as e:
                    import traceback
                    messages.error(request, f'Error updating profile: {str(e)}')
                    # Log the full error for debugging
                    print(f"Profile update error: {traceback.format_exc()}")
        
        # Handle password reset
        elif 'reset_password' in request.POST:
            current_password = request.POST.get('current_password', '')
            new_password = request.POST.get('new_password', '')
            confirm_password = request.POST.get('confirm_password', '')
            
            # Validation
            errors = []
            if not current_password:
                errors.append('Current password is required.')
            if not new_password:
                errors.append('New password is required.')
            elif len(new_password) < 8:
                errors.append('New password must be at least 8 characters long.')
            if new_password != confirm_password:
                errors.append('New passwords do not match.')
            
            if errors:
                for error in errors:
                    messages.error(request, error)
            else:
                try:
                    user = request.user
                    # Verify current password
                    if user.check_password(current_password):
                        user.set_password(new_password)
                        user.save()
                        # Update session to prevent logout
                        from django.contrib.auth import update_session_auth_hash
                        update_session_auth_hash(request, user)
                        messages.success(request, 'Password changed successfully!')
                    else:
                        messages.error(request, 'Current password is incorrect.')
                except Exception as e:
                    messages.error(request, f'Error changing password: {str(e)}')

    return render(request, 'core/settings.html', {'user': request.user})


@login_required
def autopilot_change_history(request):
    """
    Change history page showing all autopilot actions with before/after values.
    """
    from apps.autopilot.models import AutopilotExecution, AutomationRule
    from apps.amazon_auth.models import AmazonAccount
    from apps.accounts.models import Organization

    # Get user's organizations
    user_organizations = Organization.objects.filter(
        Q(owner=request.user) | Q(members=request.user)
    ).distinct()

    # Get connected Amazon accounts for user's organizations
    amazon_accounts = AmazonAccount.objects.filter(
        organization__in=user_organizations
    )

    # Get all executions with related data, filtered by user's accounts
    executions = AutopilotExecution.objects.select_related(
        'rule', 'account'
    ).filter(
        account__in=amazon_accounts
    ).order_by('-executed_at')

    # Apply filters
    status_filter = request.GET.get('status', '')
    account_filter = request.GET.get('account', '')
    rule_filter = request.GET.get('rule', '')
    entity_type_filter = request.GET.get('entity_type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if status_filter:
        executions = executions.filter(status=status_filter)

    if account_filter:
        executions = executions.filter(account_id=account_filter)

    if rule_filter:
        executions = executions.filter(rule_id=rule_filter)

    if entity_type_filter:
        executions = executions.filter(entity_type=entity_type_filter)

    if date_from:
        executions = executions.filter(executed_at__date__gte=date_from)

    if date_to:
        executions = executions.filter(executed_at__date__lte=date_to)

    # Pagination
    paginator = Paginator(executions, 50)  # 50 items per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get filter options - only for user's accounts
    accounts = amazon_accounts.order_by('account_name')

    rules = AutomationRule.objects.filter(
        goal__account__in=amazon_accounts
    ).distinct().order_by('name')

    # Get unique entity types for filter - only for user's accounts
    entity_types = AutopilotExecution.objects.filter(
        account__in=amazon_accounts
    ).values_list(
        'entity_type', flat=True
    ).distinct().order_by('entity_type')

    # Status choices
    status_choices = AutopilotExecution.STATUS_CHOICES

    context = {
        'page_obj': page_obj,
        'accounts': accounts,
        'rules': rules,
        'entity_types': entity_types,
        'status_choices': status_choices,
        'filters': {
            'status': status_filter,
            'account': account_filter,
            'rule': rule_filter,
            'entity_type': entity_type_filter,
            'date_from': date_from,
            'date_to': date_to,
        }
    }

    return render(request, 'core/autopilot_change_history.html', context)


@login_required
def analytics_overview(request):
    """
    Analytics overview page showing performance insights, quick stats, and analytics tools.
    """
    from apps.accounts.models import Organization
    from apps.amazon_auth.models import AmazonAccount
    from apps.amazon_ads.models import Campaign, AdGroup, Keyword, CampaignPerformance
    from django.db.models import Sum, Count, Avg, Q
    from datetime import datetime, timedelta
    from decimal import Decimal
    
    # Get user's organizations
    user_organizations = Organization.objects.filter(
        Q(owner=request.user) | Q(members=request.user)
    ).distinct()
    
    # Get connected Amazon accounts for user's organizations
    amazon_accounts = AmazonAccount.objects.filter(
        organization__in=user_organizations,
        is_connected=True
    )
    
    # Get campaigns for connected accounts
    campaigns = Campaign.objects.filter(account__in=amazon_accounts)
    
    # Get date range (last 30 days and 7 days)
    today = datetime.now().date()
    last_30_days = today - timedelta(days=30)
    last_7_days = today - timedelta(days=7)
    
    # Get performance data
    performance_data_30d = CampaignPerformance.objects.filter(
        campaign__in=campaigns,
        date__gte=last_30_days
    )
    
    performance_data_7d = CampaignPerformance.objects.filter(
        campaign__in=campaigns,
        date__gte=last_7_days
    )
    
    # Calculate summary stats (30 days)
    total_spend_30d = performance_data_30d.aggregate(total=Sum('cost'))['total'] or Decimal('0.00')
    total_sales_30d = performance_data_30d.aggregate(total=Sum('sales'))['total'] or Decimal('0.00')
    total_orders_30d = performance_data_30d.aggregate(total=Sum('orders'))['total'] or 0
    total_impressions_30d = performance_data_30d.aggregate(total=Sum('impressions'))['total'] or 0
    total_clicks_30d = performance_data_30d.aggregate(total=Sum('clicks'))['total'] or 0
    
    # Calculate summary stats (7 days)
    total_spend_7d = performance_data_7d.aggregate(total=Sum('cost'))['total'] or Decimal('0.00')
    total_sales_7d = performance_data_7d.aggregate(total=Sum('sales'))['total'] or Decimal('0.00')
    
    # Calculate metrics
    if total_sales_30d > 0:
        avg_acos = (float(total_spend_30d) / float(total_sales_30d)) * 100
    else:
        avg_acos = 0
    
    if total_spend_30d > 0:
        avg_roas = float(total_sales_30d) / float(total_spend_30d)
    else:
        avg_roas = 0
    
    if total_impressions_30d > 0:
        ctr = (float(total_clicks_30d) / float(total_impressions_30d)) * 100
    else:
        ctr = 0
    
    if total_clicks_30d > 0:
        cvr = (float(total_orders_30d) / float(total_clicks_30d)) * 100
    else:
        cvr = 0
    
    # Calculate daily performance trends (last 7 days)
    daily_performance = []
    for i in range(7):
        date = today - timedelta(days=6-i)
        day_data = performance_data_30d.filter(date=date).aggregate(
            spend=Sum('cost'),
            sales=Sum('sales'),
            orders=Sum('orders'),
            clicks=Sum('clicks')
        )
        daily_performance.append({
            'date': date.isoformat(),
            'spend': float(day_data['spend'] or Decimal('0.00')),
            'sales': float(day_data['sales'] or Decimal('0.00')),
            'orders': day_data['orders'] or 0,
            'clicks': day_data['clicks'] or 0,
        })
    
    # Get top performing campaigns (by sales, last 30 days)
    top_campaigns = campaigns.annotate(
        total_sales=Sum('performance_data__sales', filter=Q(performance_data__date__gte=last_30_days)),
        total_spend=Sum('performance_data__cost', filter=Q(performance_data__date__gte=last_30_days)),
        total_orders=Sum('performance_data__orders', filter=Q(performance_data__date__gte=last_30_days))
    ).filter(
        total_sales__gt=0
    ).order_by('-total_sales')[:5]
    
    # Calculate ACOS and ROAS for top campaigns
    for campaign in top_campaigns:
        if campaign.total_sales and campaign.total_sales > 0:
            campaign.calculated_acos = (float(campaign.total_spend or 0) / float(campaign.total_sales)) * 100
            campaign.calculated_roas = float(campaign.total_sales) / float(campaign.total_spend or 1)
        else:
            campaign.calculated_acos = 0
            campaign.calculated_roas = 0
    
    # Get underperforming campaigns (high ACOS or low ROAS)
    underperforming_campaigns = []
    for campaign in campaigns.annotate(
        total_sales=Sum('performance_data__sales', filter=Q(performance_data__date__gte=last_30_days)),
        total_spend=Sum('performance_data__cost', filter=Q(performance_data__date__gte=last_30_days))
    ).filter(
        total_sales__gt=0,
        state='enabled'
    ):
        campaign_acos = (float(campaign.total_spend or 0) / float(campaign.total_sales)) * 100
        if campaign_acos > 40:  # ACOS above 40%
            underperforming_campaigns.append({
                'campaign': campaign,
                'acos': campaign_acos,
                'spend': float(campaign.total_spend or 0),
                'sales': float(campaign.total_sales)
            })
    
    # Sort by ACOS descending
    underperforming_campaigns.sort(key=lambda x: x['acos'], reverse=True)
    underperforming_campaigns = underperforming_campaigns[:5]
    
    # Get keywords for performance insights
    ad_groups = AdGroup.objects.filter(campaign__in=campaigns)
    keywords = Keyword.objects.filter(ad_group__in=ad_groups)
    total_keywords = keywords.count()
    
    # Calculate growth indicators (7d vs 30d average)
    avg_daily_spend_30d = float(total_spend_30d) / 30
    avg_daily_spend_7d = float(total_spend_7d) / 7
    spend_growth = ((avg_daily_spend_7d - avg_daily_spend_30d) / avg_daily_spend_30d * 100) if avg_daily_spend_30d > 0 else 0
    
    avg_daily_sales_30d = float(total_sales_30d) / 30
    avg_daily_sales_7d = float(total_sales_7d) / 7
    sales_growth = ((avg_daily_sales_7d - avg_daily_sales_30d) / avg_daily_sales_30d * 100) if avg_daily_sales_30d > 0 else 0
    
    context = {
        'total_spend_30d': float(total_spend_30d),
        'total_spend_7d': float(total_spend_7d),
        'total_sales_30d': float(total_sales_30d),
        'total_sales_7d': float(total_sales_7d),
        'total_orders_30d': total_orders_30d,
        'total_impressions_30d': total_impressions_30d,
        'total_clicks_30d': total_clicks_30d,
        'avg_acos': avg_acos,
        'avg_roas': avg_roas,
        'ctr': ctr,
        'cvr': cvr,
        'daily_performance': daily_performance,
        'top_campaigns': top_campaigns,
        'underperforming_campaigns': underperforming_campaigns,
        'total_keywords': total_keywords,
        'spend_growth': spend_growth,
        'sales_growth': sales_growth,
        'date_range': {
            'start': last_30_days,
            'end': today
        }
    }
    
    return render(request, 'core/analytics.html', context)


@login_required
def analytics_performance_reports(request):
    """
    Performance reports page with report generation, custom date ranges, campaign/keyword reports, export, and scheduled reports.
    """
    from apps.accounts.models import Organization
    from apps.amazon_auth.models import AmazonAccount
    from apps.amazon_ads.models import Campaign, AdGroup, Keyword, CampaignPerformance, KeywordPerformance
    from django.db.models import Sum, Count, Avg, Q
    from django.http import HttpResponse
    from datetime import datetime, timedelta
    from decimal import Decimal
    import csv
    import json
    
    # Get user's organizations
    user_organizations = Organization.objects.filter(
        Q(owner=request.user) | Q(members=request.user)
    ).distinct()
    
    # Get connected Amazon accounts
    amazon_accounts = AmazonAccount.objects.filter(
        organization__in=user_organizations,
        is_connected=True
    )
    
    # Get campaigns
    campaigns = Campaign.objects.filter(account__in=amazon_accounts)
    
    # Handle date range from request
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    report_type = request.GET.get('report_type', 'campaign')  # 'campaign' or 'keyword'
    account_filter = request.GET.get('account', '')
    campaign_filter = request.GET.get('campaign', '')
    
    # Default to last 30 days if no dates provided
    today = datetime.now().date()
    if not date_from:
        date_from = (today - timedelta(days=30)).isoformat()
    if not date_to:
        date_to = today.isoformat()
    
    try:
        date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
        date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
    except:
        date_from_obj = today - timedelta(days=30)
        date_to_obj = today
    
    # Filter campaigns if account/campaign filter is applied
    filtered_campaigns = campaigns
    if account_filter:
        filtered_campaigns = filtered_campaigns.filter(account_id=account_filter)
    if campaign_filter:
        filtered_campaigns = filtered_campaigns.filter(id=campaign_filter)
    
    # Handle export requests
    export_format = request.GET.get('export', '')
    if export_format in ['csv', 'excel']:
        if report_type == 'campaign':
            # Campaign performance report
            performance_data = CampaignPerformance.objects.filter(
                campaign__in=filtered_campaigns,
                date__gte=date_from_obj,
                date__lte=date_to_obj
            ).select_related('campaign', 'campaign__account')
            
            # Aggregate by campaign
            campaign_report = []
            for campaign in filtered_campaigns:
                camp_perf = performance_data.filter(campaign=campaign).aggregate(
                    total_spend=Sum('cost'),
                    total_sales=Sum('sales'),
                    total_orders=Sum('orders'),
                    total_impressions=Sum('impressions'),
                    total_clicks=Sum('clicks')
                )
                
                if camp_perf['total_spend'] or camp_perf['total_sales']:
                    acos = 0
                    roas = 0
                    if camp_perf['total_sales'] and camp_perf['total_sales'] > 0:
                        acos = (float(camp_perf['total_spend'] or 0) / float(camp_perf['total_sales'])) * 100
                        roas = float(camp_perf['total_sales']) / float(camp_perf['total_spend'] or 1)
                    
                    ctr = 0
                    if camp_perf['total_impressions'] and camp_perf['total_impressions'] > 0:
                        ctr = (float(camp_perf['total_clicks'] or 0) / float(camp_perf['total_impressions'])) * 100
                    
                    cvr = 0
                    if camp_perf['total_clicks'] and camp_perf['total_clicks'] > 0:
                        cvr = (float(camp_perf['total_orders'] or 0) / float(camp_perf['total_clicks'])) * 100
                    
                    campaign_report.append({
                        'Campaign Name': campaign.name,
                        'Campaign ID': campaign.campaign_id,
                        'Account': campaign.account.account_name,
                        'Type': campaign.get_campaign_type_display(),
                        'Status': campaign.get_state_display(),
                        'Spend': float(camp_perf['total_spend'] or 0),
                        'Sales': float(camp_perf['total_sales'] or 0),
                        'Orders': camp_perf['total_orders'] or 0,
                        'Impressions': camp_perf['total_impressions'] or 0,
                        'Clicks': camp_perf['total_clicks'] or 0,
                        'ACOS': round(acos, 2),
                        'ROAS': round(roas, 2),
                        'CTR': round(ctr, 2),
                        'CVR': round(cvr, 2),
                    })
            
            # Generate CSV response
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="campaign_performance_{date_from_obj}_{date_to_obj}.csv"'
            
            if campaign_report:
                writer = csv.DictWriter(response, fieldnames=campaign_report[0].keys())
                writer.writeheader()
                writer.writerows(campaign_report)
            else:
                response.write('No data available for the selected date range.\n')
            
            return response
        
        elif report_type == 'keyword':
            # Keyword performance report
            ad_groups = AdGroup.objects.filter(campaign__in=filtered_campaigns)
            keywords = Keyword.objects.filter(ad_group__in=ad_groups)
            
            keyword_perf_data = KeywordPerformance.objects.filter(
                keyword__in=keywords,
                date__gte=date_from_obj,
                date__lte=date_to_obj
            ).select_related('keyword', 'keyword__ad_group', 'keyword__ad_group__campaign')
            
            # Aggregate by keyword
            keyword_report = []
            for keyword in keywords:
                kw_perf = keyword_perf_data.filter(keyword=keyword).aggregate(
                    total_spend=Sum('cost'),
                    total_sales=Sum('sales'),
                    total_orders=Sum('orders'),
                    total_impressions=Sum('impressions'),
                    total_clicks=Sum('clicks')
                )
                
                if kw_perf['total_spend'] or kw_perf['total_sales']:
                    acos = 0
                    roas = 0
                    if kw_perf['total_sales'] and kw_perf['total_sales'] > 0:
                        acos = (float(kw_perf['total_spend'] or 0) / float(kw_perf['total_sales'])) * 100
                        roas = float(kw_perf['total_sales']) / float(kw_perf['total_spend'] or 1)
                    
                    ctr = 0
                    if kw_perf['total_impressions'] and kw_perf['total_impressions'] > 0:
                        ctr = (float(kw_perf['total_clicks'] or 0) / float(kw_perf['total_impressions'])) * 100
                    
                    cvr = 0
                    if kw_perf['total_clicks'] and kw_perf['total_clicks'] > 0:
                        cvr = (float(kw_perf['total_orders'] or 0) / float(kw_perf['total_clicks'])) * 100
                    
                    keyword_report.append({
                        'Keyword': keyword.keyword_text,
                        'Match Type': keyword.get_match_type_display(),
                        'Campaign': keyword.ad_group.campaign.name,
                        'Ad Group': keyword.ad_group.name,
                        'Status': keyword.get_state_display(),
                        'Bid': float(keyword.bid or 0),
                        'Spend': float(kw_perf['total_spend'] or 0),
                        'Sales': float(kw_perf['total_sales'] or 0),
                        'Orders': kw_perf['total_orders'] or 0,
                        'Impressions': kw_perf['total_impressions'] or 0,
                        'Clicks': kw_perf['total_clicks'] or 0,
                        'ACOS': round(acos, 2),
                        'ROAS': round(roas, 2),
                        'CTR': round(ctr, 2),
                        'CVR': round(cvr, 2),
                    })
            
            # Generate CSV response
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="keyword_performance_{date_from_obj}_{date_to_obj}.csv"'
            
            if keyword_report:
                writer = csv.DictWriter(response, fieldnames=keyword_report[0].keys())
                writer.writeheader()
                writer.writerows(keyword_report)
            else:
                response.write('No data available for the selected date range.\n')
            
            return response
    
    # Get campaign performance data for display
    campaign_performance_data = CampaignPerformance.objects.filter(
        campaign__in=filtered_campaigns,
        date__gte=date_from_obj,
        date__lte=date_to_obj
    )
    
    # Aggregate campaign performance
    campaign_reports = []
    for campaign in filtered_campaigns:
        perf = campaign_performance_data.filter(campaign=campaign).aggregate(
            total_spend=Sum('cost'),
            total_sales=Sum('sales'),
            total_orders=Sum('orders'),
            total_impressions=Sum('impressions'),
            total_clicks=Sum('clicks')
        )
        
        if perf['total_spend'] or perf['total_sales']:
            acos = 0
            roas = 0
            if perf['total_sales'] and perf['total_sales'] > 0:
                acos = (float(perf['total_spend'] or 0) / float(perf['total_sales'])) * 100
                roas = float(perf['total_sales']) / float(perf['total_spend'] or 1)
            
            ctr = 0
            if perf['total_impressions'] and perf['total_impressions'] > 0:
                ctr = (float(perf['total_clicks'] or 0) / float(perf['total_impressions'])) * 100
            
            cvr = 0
            if perf['total_clicks'] and perf['total_clicks'] > 0:
                cvr = (float(perf['total_orders'] or 0) / float(perf['total_clicks'])) * 100
            
            campaign_reports.append({
                'campaign': campaign,
                'spend': float(perf['total_spend'] or 0),
                'sales': float(perf['total_sales'] or 0),
                'orders': perf['total_orders'] or 0,
                'impressions': perf['total_impressions'] or 0,
                'clicks': perf['total_clicks'] or 0,
                'acos': acos,
                'roas': roas,
                'ctr': ctr,
                'cvr': cvr,
            })
    
    # Get keyword performance data for display
    ad_groups = AdGroup.objects.filter(campaign__in=filtered_campaigns)
    keywords = Keyword.objects.filter(ad_group__in=ad_groups)
    
    keyword_perf_data = KeywordPerformance.objects.filter(
        keyword__in=keywords,
        date__gte=date_from_obj,
        date__lte=date_to_obj
    )
    
    # Aggregate keyword performance
    keyword_reports = []
    for keyword in keywords[:100]:  # Limit to 100 for display
        kw_perf = keyword_perf_data.filter(keyword=keyword).aggregate(
            total_spend=Sum('cost'),
            total_sales=Sum('sales'),
            total_orders=Sum('orders'),
            total_impressions=Sum('impressions'),
            total_clicks=Sum('clicks')
        )
        
        if kw_perf['total_spend'] or kw_perf['total_sales']:
            acos = 0
            roas = 0
            if kw_perf['total_sales'] and kw_perf['total_sales'] > 0:
                acos = (float(kw_perf['total_spend'] or 0) / float(kw_perf['total_sales'])) * 100
                roas = float(kw_perf['total_sales']) / float(kw_perf['total_spend'] or 1)
            
            ctr = 0
            if kw_perf['total_impressions'] and kw_perf['total_impressions'] > 0:
                ctr = (float(kw_perf['total_clicks'] or 0) / float(kw_perf['total_impressions'])) * 100
            
            cvr = 0
            if kw_perf['total_clicks'] and kw_perf['total_clicks'] > 0:
                cvr = (float(kw_perf['total_orders'] or 0) / float(kw_perf['total_clicks'])) * 100
            
            keyword_reports.append({
                'keyword': keyword,
                'spend': float(kw_perf['total_spend'] or 0),
                'sales': float(kw_perf['total_sales'] or 0),
                'orders': kw_perf['total_orders'] or 0,
                'impressions': kw_perf['total_impressions'] or 0,
                'clicks': kw_perf['total_clicks'] or 0,
                'acos': acos,
                'roas': roas,
                'ctr': ctr,
                'cvr': cvr,
            })
    
    # Sort reports
    campaign_reports.sort(key=lambda x: x['sales'], reverse=True)
    keyword_reports.sort(key=lambda x: x['sales'], reverse=True)
    
    # Get scheduled reports (placeholder - Phase 2 will implement)
    scheduled_reports = []
    
    context = {
        'amazon_accounts': amazon_accounts,
        'campaigns': campaigns,
        'date_from': date_from_obj.isoformat(),
        'date_to': date_to_obj.isoformat(),
        'report_type': report_type,
        'account_filter': account_filter,
        'campaign_filter': campaign_filter,
        'campaign_reports': campaign_reports,
        'keyword_reports': keyword_reports,
        'scheduled_reports': scheduled_reports,
    }
    
    return render(request, 'core/analytics_performance_reports.html', context)


@login_required
def analytics_keyword_performance(request):
    """
    Detailed keyword performance analysis page with metrics, trends, top/underperforming keywords, and recommendations.
    """
    from apps.accounts.models import Organization
    from apps.amazon_auth.models import AmazonAccount
    from apps.amazon_ads.models import Campaign, AdGroup, Keyword, KeywordPerformance
    from django.db.models import Sum, Count, Avg, Q
    from datetime import datetime, timedelta
    from decimal import Decimal
    
    # Get user's organizations
    user_organizations = Organization.objects.filter(
        Q(owner=request.user) | Q(members=request.user)
    ).distinct()
    
    # Get connected Amazon accounts
    amazon_accounts = AmazonAccount.objects.filter(
        organization__in=user_organizations,
        is_connected=True
    )
    
    # Get campaigns
    campaigns = Campaign.objects.filter(account__in=amazon_accounts)
    
    # Handle date range from request
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    account_filter = request.GET.get('account', '')
    campaign_filter = request.GET.get('campaign', '')
    
    # Default to last 30 days if no dates provided
    today = datetime.now().date()
    if not date_from:
        date_from_obj = today - timedelta(days=30)
    else:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
        except:
            date_from_obj = today - timedelta(days=30)
    
    if not date_to:
        date_to_obj = today
    else:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
        except:
            date_to_obj = today
    
    # Filter campaigns if account/campaign filter is applied
    filtered_campaigns = campaigns
    if account_filter:
        filtered_campaigns = filtered_campaigns.filter(account_id=account_filter)
    if campaign_filter:
        filtered_campaigns = filtered_campaigns.filter(id=campaign_filter)
    
    # Get ad groups and keywords
    ad_groups = AdGroup.objects.filter(campaign__in=filtered_campaigns)
    keywords = Keyword.objects.filter(ad_group__in=ad_groups)
    
    # Get keyword performance data
    keyword_perf_data = KeywordPerformance.objects.filter(
        keyword__in=keywords,
        date__gte=date_from_obj,
        date__lte=date_to_obj
    ).select_related('keyword', 'keyword__ad_group', 'keyword__ad_group__campaign')
    
    # Calculate overall keyword metrics
    overall_metrics = keyword_perf_data.aggregate(
        total_spend=Sum('cost'),
        total_sales=Sum('sales'),
        total_orders=Sum('orders'),
        total_impressions=Sum('impressions'),
        total_clicks=Sum('clicks')
    )
    
    # Calculate average metrics
    avg_ctr = 0
    avg_cvr = 0
    avg_acos = 0
    avg_roas = 0
    
    if overall_metrics['total_impressions'] and overall_metrics['total_impressions'] > 0:
        avg_ctr = (float(overall_metrics['total_clicks'] or 0) / float(overall_metrics['total_impressions'])) * 100
    
    if overall_metrics['total_clicks'] and overall_metrics['total_clicks'] > 0:
        avg_cvr = (float(overall_metrics['total_orders'] or 0) / float(overall_metrics['total_clicks'])) * 100
    
    if overall_metrics['total_sales'] and overall_metrics['total_sales'] > 0:
        avg_acos = (float(overall_metrics['total_spend'] or 0) / float(overall_metrics['total_sales'])) * 100
        avg_roas = float(overall_metrics['total_sales']) / float(overall_metrics['total_spend'] or 1)
    
    # Calculate performance trends (daily for last 7 days)
    daily_trends = []
    for i in range(7):
        date = today - timedelta(days=6-i)
        day_data = keyword_perf_data.filter(date=date).aggregate(
            spend=Sum('cost'),
            sales=Sum('sales'),
            orders=Sum('orders'),
            clicks=Sum('clicks'),
            impressions=Sum('impressions')
        )
        
        day_ctr = 0
        day_cvr = 0
        day_acos = 0
        day_roas = 0
        
        if day_data['impressions'] and day_data['impressions'] > 0:
            day_ctr = (float(day_data['clicks'] or 0) / float(day_data['impressions'])) * 100
        
        if day_data['clicks'] and day_data['clicks'] > 0:
            day_cvr = (float(day_data['orders'] or 0) / float(day_data['clicks'])) * 100
        
        if day_data['sales'] and day_data['sales'] > 0:
            day_acos = (float(day_data['spend'] or 0) / float(day_data['sales'])) * 100
            day_roas = float(day_data['sales']) / float(day_data['spend'] or 1)
        
        daily_trends.append({
            'date': date.isoformat(),
            'ctr': day_ctr,
            'cvr': day_cvr,
            'acos': day_acos,
            'roas': day_roas,
            'spend': float(day_data['spend'] or 0),
            'sales': float(day_data['sales'] or 0),
        })
    
    # Get top performing keywords
    top_keywords = []
    for keyword in keywords:
        kw_perf = keyword_perf_data.filter(keyword=keyword).aggregate(
            total_spend=Sum('cost'),
            total_sales=Sum('sales'),
            total_orders=Sum('orders'),
            total_impressions=Sum('impressions'),
            total_clicks=Sum('clicks')
        )
        
        if kw_perf['total_sales'] and kw_perf['total_sales'] > 0:
            acos = (float(kw_perf['total_spend'] or 0) / float(kw_perf['total_sales'])) * 100
            roas = float(kw_perf['total_sales']) / float(kw_perf['total_spend'] or 1)
            
            ctr = 0
            if kw_perf['total_impressions'] and kw_perf['total_impressions'] > 0:
                ctr = (float(kw_perf['total_clicks'] or 0) / float(kw_perf['total_impressions'])) * 100
            
            cvr = 0
            if kw_perf['total_clicks'] and kw_perf['total_clicks'] > 0:
                cvr = (float(kw_perf['total_orders'] or 0) / float(kw_perf['total_clicks'])) * 100
            
            top_keywords.append({
                'keyword': keyword,
                'spend': float(kw_perf['total_spend'] or 0),
                'sales': float(kw_perf['total_sales'] or 0),
                'orders': kw_perf['total_orders'] or 0,
                'impressions': kw_perf['total_impressions'] or 0,
                'clicks': kw_perf['total_clicks'] or 0,
                'acos': acos,
                'roas': roas,
                'ctr': ctr,
                'cvr': cvr,
            })
    
    # Sort by sales descending
    top_keywords.sort(key=lambda x: x['sales'], reverse=True)
    top_keywords = top_keywords[:10]  # Top 10
    
    # Get underperforming keywords
    underperforming_keywords = []
    for keyword in keywords:
        kw_perf = keyword_perf_data.filter(keyword=keyword).aggregate(
            total_spend=Sum('cost'),
            total_sales=Sum('sales'),
            total_orders=Sum('orders'),
            total_impressions=Sum('impressions'),
            total_clicks=Sum('clicks')
        )
        
        if kw_perf['total_spend'] and kw_perf['total_spend'] > 0:
            acos = 0
            if kw_perf['total_sales'] and kw_perf['total_sales'] > 0:
                acos = (float(kw_perf['total_spend'] or 0) / float(kw_perf['total_sales'])) * 100
            
            # Consider underperforming if: high ACOS (>40%), low sales, or no sales
            if (kw_perf['total_sales'] and kw_perf['total_sales'] > 0 and acos > 40) or (kw_perf['total_sales'] == 0 and kw_perf['total_spend'] > 10):
                roas = 0
                if kw_perf['total_sales'] and kw_perf['total_sales'] > 0:
                    roas = float(kw_perf['total_sales']) / float(kw_perf['total_spend'] or 1)
                
                ctr = 0
                if kw_perf['total_impressions'] and kw_perf['total_impressions'] > 0:
                    ctr = (float(kw_perf['total_clicks'] or 0) / float(kw_perf['total_impressions'])) * 100
                
                cvr = 0
                if kw_perf['total_clicks'] and kw_perf['total_clicks'] > 0:
                    cvr = (float(kw_perf['total_orders'] or 0) / float(kw_perf['total_clicks'])) * 100
                
                underperforming_keywords.append({
                    'keyword': keyword,
                    'spend': float(kw_perf['total_spend'] or 0),
                    'sales': float(kw_perf['total_sales'] or 0),
                    'orders': kw_perf['total_orders'] or 0,
                    'impressions': kw_perf['total_impressions'] or 0,
                    'clicks': kw_perf['total_clicks'] or 0,
                    'acos': acos,
                    'roas': roas,
                    'ctr': ctr,
                    'cvr': cvr,
                    'issue': 'High ACOS' if acos > 40 else 'No Sales',
                })
    
    # Sort by ACOS descending (worst first)
    underperforming_keywords.sort(key=lambda x: x['acos'] if x['acos'] > 0 else 999, reverse=True)
    underperforming_keywords = underperforming_keywords[:10]  # Top 10 underperformers
    
    # Generate recommendations
    recommendations = []
    
    # Recommendation 1: High ACOS keywords
    high_acos_count = len([kw for kw in underperforming_keywords if kw['acos'] > 40])
    if high_acos_count > 0:
        recommendations.append({
            'type': 'warning',
            'title': f'{high_acos_count} Keywords with High ACOS',
            'description': 'Consider reducing bids or pausing these keywords to improve profitability.',
            'action': 'Review underperforming keywords below',
        })
    
    # Recommendation 2: Low CTR keywords
    low_ctr_keywords = [kw for kw in top_keywords if kw['ctr'] < 0.5 and kw['impressions'] > 100]
    if low_ctr_keywords:
        recommendations.append({
            'type': 'info',
            'title': f'{len(low_ctr_keywords)} Keywords with Low CTR',
            'description': 'These keywords have low click-through rates. Consider improving ad copy or relevance.',
            'action': 'Optimize ad copy and targeting',
        })
    
    # Recommendation 3: High performing keywords
    high_performers = [kw for kw in top_keywords if kw['roas'] > 3 and kw['sales'] > 100]
    if high_performers:
        recommendations.append({
            'type': 'success',
            'title': f'{len(high_performers)} High-Performing Keywords',
            'description': 'These keywords are generating excellent returns. Consider increasing bids to capture more traffic.',
            'action': 'Increase bids on top performers',
        })
    
    # Recommendation 4: Keywords with no impressions
    no_impressions = keywords.filter(
        id__in=[kw.id for kw in keywords if not keyword_perf_data.filter(keyword=kw, impressions__gt=0).exists()]
    ).count()
    if no_impressions > 0:
        recommendations.append({
            'type': 'warning',
            'title': f'{no_impressions} Keywords with No Impressions',
            'description': 'These keywords are not receiving any traffic. Consider increasing bids or checking match types.',
            'action': 'Review keyword bids and match types',
        })
    
    context = {
        'amazon_accounts': amazon_accounts,
        'campaigns': campaigns,
        'date_from': date_from_obj.isoformat(),
        'date_to': date_to_obj.isoformat(),
        'account_filter': account_filter,
        'campaign_filter': campaign_filter,
        'avg_ctr': avg_ctr,
        'avg_cvr': avg_cvr,
        'avg_acos': avg_acos,
        'avg_roas': avg_roas,
        'total_spend': float(overall_metrics['total_spend'] or 0),
        'total_sales': float(overall_metrics['total_sales'] or 0),
        'total_orders': overall_metrics['total_orders'] or 0,
        'total_impressions': overall_metrics['total_impressions'] or 0,
        'total_clicks': overall_metrics['total_clicks'] or 0,
        'daily_trends': daily_trends,
        'top_keywords': top_keywords,
        'underperforming_keywords': underperforming_keywords,
        'recommendations': recommendations,
    }
    
    return render(request, 'core/analytics_keyword_performance.html', context)


@login_required
def analytics_campaign_trends(request):
    """
    Campaign trends analysis page showing performance trends over time with comparative analysis, period-over-period comparison, and trend alerts.
    """
    from apps.accounts.models import Organization
    from apps.amazon_auth.models import AmazonAccount
    from apps.amazon_ads.models import Campaign, CampaignPerformance
    from django.db.models import Sum, Count, Avg, Q
    from datetime import datetime, timedelta
    from decimal import Decimal
    
    # Get user's organizations
    user_organizations = Organization.objects.filter(
        Q(owner=request.user) | Q(members=request.user)
    ).distinct()
    
    # Get connected Amazon accounts
    amazon_accounts = AmazonAccount.objects.filter(
        organization__in=user_organizations,
        is_connected=True
    )
    
    # Get campaigns
    campaigns = Campaign.objects.filter(account__in=amazon_accounts)
    
    # Handle date range from request
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    account_filter = request.GET.get('account', '')
    campaign_filter = request.GET.get('campaign', '')
    compare_period = request.GET.get('compare_period', 'previous')  # 'previous' or 'year'
    
    # Default to last 30 days if no dates provided
    today = datetime.now().date()
    if not date_from:
        date_from_obj = today - timedelta(days=30)
    else:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
        except:
            date_from_obj = today - timedelta(days=30)
    
    if not date_to:
        date_to_obj = today
    else:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
        except:
            date_to_obj = today
    
    # Filter campaigns if account/campaign filter is applied
    filtered_campaigns = campaigns
    if account_filter:
        filtered_campaigns = filtered_campaigns.filter(account_id=account_filter)
    if campaign_filter:
        filtered_campaigns = filtered_campaigns.filter(id=campaign_filter)
    
    # Calculate period length for comparison
    period_length = (date_to_obj - date_from_obj).days
    
    # Get current period performance data
    current_perf_data = CampaignPerformance.objects.filter(
        campaign__in=filtered_campaigns,
        date__gte=date_from_obj,
        date__lte=date_to_obj
    )
    
    # Calculate current period metrics
    current_metrics = current_perf_data.aggregate(
        total_spend=Sum('cost'),
        total_sales=Sum('sales'),
        total_orders=Sum('orders'),
        total_impressions=Sum('impressions'),
        total_clicks=Sum('clicks')
    )
    
    current_acos = 0
    current_roas = 0
    current_ctr = 0
    current_cvr = 0
    
    if current_metrics['total_sales'] and current_metrics['total_sales'] > 0:
        current_acos = (float(current_metrics['total_spend'] or 0) / float(current_metrics['total_sales'])) * 100
        current_roas = float(current_metrics['total_sales']) / float(current_metrics['total_spend'] or 1)
    
    if current_metrics['total_impressions'] and current_metrics['total_impressions'] > 0:
        current_ctr = (float(current_metrics['total_clicks'] or 0) / float(current_metrics['total_impressions'])) * 100
    
    if current_metrics['total_clicks'] and current_metrics['total_clicks'] > 0:
        current_cvr = (float(current_metrics['total_orders'] or 0) / float(current_metrics['total_clicks'])) * 100
    
    # Calculate comparison period dates
    if compare_period == 'previous':
        # Previous period (same length, before current period)
        compare_date_to_obj = date_from_obj - timedelta(days=1)
        compare_date_from_obj = compare_date_to_obj - timedelta(days=period_length)
    else:
        # Year over year (same dates, previous year)
        compare_date_from_obj = date_from_obj - timedelta(days=365)
        compare_date_to_obj = date_to_obj - timedelta(days=365)
    
    # Get comparison period performance data
    compare_perf_data = CampaignPerformance.objects.filter(
        campaign__in=filtered_campaigns,
        date__gte=compare_date_from_obj,
        date__lte=compare_date_to_obj
    )
    
    # Calculate comparison period metrics
    compare_metrics = compare_perf_data.aggregate(
        total_spend=Sum('cost'),
        total_sales=Sum('sales'),
        total_orders=Sum('orders'),
        total_impressions=Sum('impressions'),
        total_clicks=Sum('clicks')
    )
    
    compare_acos = 0
    compare_roas = 0
    compare_ctr = 0
    compare_cvr = 0
    
    if compare_metrics['total_sales'] and compare_metrics['total_sales'] > 0:
        compare_acos = (float(compare_metrics['total_spend'] or 0) / float(compare_metrics['total_sales'])) * 100
        compare_roas = float(compare_metrics['total_sales']) / float(compare_metrics['total_spend'] or 1)
    
    if compare_metrics['total_impressions'] and compare_metrics['total_impressions'] > 0:
        compare_ctr = (float(compare_metrics['total_clicks'] or 0) / float(compare_metrics['total_impressions'])) * 100
    
    if compare_metrics['total_clicks'] and compare_metrics['total_clicks'] > 0:
        compare_cvr = (float(compare_metrics['total_orders'] or 0) / float(compare_metrics['total_clicks'])) * 100
    
    # Calculate period-over-period changes
    spend_change = 0
    sales_change = 0
    acos_change = 0
    roas_change = 0
    ctr_change = 0
    cvr_change = 0
    
    if compare_metrics['total_spend'] and compare_metrics['total_spend'] > 0:
        spend_change = ((float(current_metrics['total_spend'] or 0) - float(compare_metrics['total_spend'])) / float(compare_metrics['total_spend'])) * 100
    
    if compare_metrics['total_sales'] and compare_metrics['total_sales'] > 0:
        sales_change = ((float(current_metrics['total_sales'] or 0) - float(compare_metrics['total_sales'])) / float(compare_metrics['total_sales'])) * 100
    
    if compare_acos > 0:
        acos_change = current_acos - compare_acos
    
    if compare_roas > 0:
        roas_change = ((current_roas - compare_roas) / compare_roas) * 100
    
    if compare_ctr > 0:
        ctr_change = current_ctr - compare_ctr
    
    if compare_cvr > 0:
        cvr_change = current_cvr - compare_cvr
    
    # Generate daily trends for current period
    daily_trends = []
    current_date = date_from_obj
    while current_date <= date_to_obj:
        day_data = current_perf_data.filter(date=current_date).aggregate(
            spend=Sum('cost'),
            sales=Sum('sales'),
            orders=Sum('orders'),
            clicks=Sum('clicks'),
            impressions=Sum('impressions')
        )
        
        day_acos = 0
        day_roas = 0
        if day_data['sales'] and day_data['sales'] > 0:
            day_acos = (float(day_data['spend'] or 0) / float(day_data['sales'])) * 100
            day_roas = float(day_data['sales']) / float(day_data['spend'] or 1)
        
        daily_trends.append({
            'date': current_date.isoformat(),
            'spend': float(day_data['spend'] or 0),
            'sales': float(day_data['sales'] or 0),
            'orders': day_data['orders'] or 0,
            'clicks': day_data['clicks'] or 0,
            'impressions': day_data['impressions'] or 0,
            'acos': day_acos,
            'roas': day_roas,
        })
        
        current_date += timedelta(days=1)
    
    # Generate trend alerts
    trend_alerts = []
    
    # Alert 1: Significant spend increase
    if spend_change > 20:
        trend_alerts.append({
            'type': 'warning',
            'title': 'Significant Spend Increase',
            'description': f'Spend increased by {spend_change:.1f}% compared to previous period. Review campaign performance.',
            'severity': 'high' if spend_change > 50 else 'medium',
        })
    
    # Alert 2: Sales decline
    if sales_change < -10:
        trend_alerts.append({
            'type': 'error',
            'title': 'Sales Decline',
            'description': f'Sales decreased by {abs(sales_change):.1f}% compared to previous period. Investigate campaign performance.',
            'severity': 'high' if sales_change < -20 else 'medium',
        })
    
    # Alert 3: ACOS increase
    if acos_change > 5:
        trend_alerts.append({
            'type': 'warning',
            'title': 'ACOS Increase',
            'description': f'ACOS increased by {acos_change:.1f} percentage points. Consider optimizing campaigns.',
            'severity': 'high' if acos_change > 10 else 'medium',
        })
    
    # Alert 4: ROAS decline
    if roas_change < -10:
        trend_alerts.append({
            'type': 'warning',
            'title': 'ROAS Decline',
            'description': f'ROAS decreased by {abs(roas_change):.1f}% compared to previous period.',
            'severity': 'high' if roas_change < -20 else 'medium',
        })
    
    # Alert 5: Positive trends
    if sales_change > 10 and acos_change < -2:
        trend_alerts.append({
            'type': 'success',
            'title': 'Strong Performance',
            'description': f'Sales increased by {sales_change:.1f}% while ACOS improved by {abs(acos_change):.1f} percentage points.',
            'severity': 'low',
        })
    
    # Get campaign-level trends for comparative analysis
    campaign_trends = []
    for campaign in filtered_campaigns[:10]:  # Limit to 10 campaigns
        camp_current = current_perf_data.filter(campaign=campaign).aggregate(
            spend=Sum('cost'),
            sales=Sum('sales'),
            orders=Sum('orders')
        )
        
        camp_compare = compare_perf_data.filter(campaign=campaign).aggregate(
            spend=Sum('cost'),
            sales=Sum('sales'),
            orders=Sum('orders')
        )
        
        if camp_current['spend'] or camp_compare['spend']:
            camp_spend_change = 0
            camp_sales_change = 0
            
            if camp_compare['spend'] and camp_compare['spend'] > 0:
                camp_spend_change = ((float(camp_current['spend'] or 0) - float(camp_compare['spend'])) / float(camp_compare['spend'])) * 100
            
            if camp_compare['sales'] and camp_compare['sales'] > 0:
                camp_sales_change = ((float(camp_current['sales'] or 0) - float(camp_compare['sales'])) / float(camp_compare['sales'])) * 100
            
            campaign_trends.append({
                'campaign': campaign,
                'current_spend': float(camp_current['spend'] or 0),
                'current_sales': float(camp_current['sales'] or 0),
                'compare_spend': float(camp_compare['spend'] or 0),
                'compare_sales': float(camp_compare['sales'] or 0),
                'spend_change': camp_spend_change,
                'sales_change': camp_sales_change,
            })
    
    # Sort by sales change
    campaign_trends.sort(key=lambda x: x['sales_change'], reverse=True)
    
    context = {
        'amazon_accounts': amazon_accounts,
        'campaigns': campaigns,
        'date_from': date_from_obj.isoformat(),
        'date_to': date_to_obj.isoformat(),
        'account_filter': account_filter,
        'campaign_filter': campaign_filter,
        'compare_period': compare_period,
        'current_metrics': {
            'spend': float(current_metrics['total_spend'] or 0),
            'sales': float(current_metrics['total_sales'] or 0),
            'orders': current_metrics['total_orders'] or 0,
            'impressions': current_metrics['total_impressions'] or 0,
            'clicks': current_metrics['total_clicks'] or 0,
            'acos': current_acos,
            'roas': current_roas,
            'ctr': current_ctr,
            'cvr': current_cvr,
        },
        'compare_metrics': {
            'spend': float(compare_metrics['total_spend'] or 0),
            'sales': float(compare_metrics['total_sales'] or 0),
            'orders': compare_metrics['total_orders'] or 0,
            'impressions': compare_metrics['total_impressions'] or 0,
            'clicks': compare_metrics['total_clicks'] or 0,
            'acos': compare_acos,
            'roas': compare_roas,
            'ctr': compare_ctr,
            'cvr': compare_cvr,
        },
        'changes': {
            'spend': spend_change,
            'sales': sales_change,
            'acos': acos_change,
            'roas': roas_change,
            'ctr': ctr_change,
            'cvr': cvr_change,
        },
        'daily_trends': daily_trends,
        'campaign_trends': campaign_trends,
        'trend_alerts': trend_alerts,
        'compare_date_from': compare_date_from_obj.isoformat(),
        'compare_date_to': compare_date_to_obj.isoformat(),
    }
    
    return render(request, 'core/analytics_campaign_trends.html', context)


@login_required
def analytics_date_filters(request):
    """
    Date filtering functionality page for analytics pages with custom date ranges, presets, compare periods, and timezone settings.
    """
    from datetime import datetime, timedelta
    from django.contrib import messages
    import pytz
    
    # Handle POST requests to save preferences
    if request.method == 'POST':
        # Save date filter preferences (Phase 2: Store in user profile/settings)
        default_date_range = request.POST.get('default_date_range', '30')
        default_compare_period = request.POST.get('default_compare_period', 'previous')
        timezone = request.POST.get('timezone', 'UTC')
        
        # Validate timezone
        try:
            pytz.timezone(timezone)
        except pytz.exceptions.UnknownTimeZoneError:
            messages.error(request, 'Invalid timezone selected.')
            timezone = 'UTC'
        
        messages.success(request, 'Date filter preferences saved successfully.')
    
    # Get current date for presets
    today = datetime.now().date()
    
    # Calculate preset ranges
    presets = {
        'last_7_days': {
            'label': 'Last 7 Days',
            'from': (today - timedelta(days=7)).isoformat(),
            'to': today.isoformat(),
        },
        'last_30_days': {
            'label': 'Last 30 Days',
            'from': (today - timedelta(days=30)).isoformat(),
            'to': today.isoformat(),
        },
        'last_90_days': {
            'label': 'Last 90 Days',
            'from': (today - timedelta(days=90)).isoformat(),
            'to': today.isoformat(),
        },
        'this_month': {
            'label': 'This Month',
            'from': today.replace(day=1).isoformat(),
            'to': today.isoformat(),
        },
        'last_month': {
            'label': 'Last Month',
            'from': (today.replace(day=1) - timedelta(days=1)).replace(day=1).isoformat(),
            'to': (today.replace(day=1) - timedelta(days=1)).isoformat(),
        },
        'this_quarter': {
            'label': 'This Quarter',
            'from': today.replace(month=((today.month - 1) // 3) * 3 + 1, day=1).isoformat(),
            'to': today.isoformat(),
        },
        'last_quarter': {
            'label': 'Last Quarter',
            'from': ((today.replace(month=((today.month - 1) // 3) * 3 + 1, day=1) - timedelta(days=1)).replace(day=1)).isoformat(),
            'to': (today.replace(month=((today.month - 1) // 3) * 3 + 1, day=1) - timedelta(days=1)).isoformat(),
        },
        'this_year': {
            'label': 'This Year',
            'from': today.replace(month=1, day=1).isoformat(),
            'to': today.isoformat(),
        },
        'last_year': {
            'label': 'Last Year',
            'from': today.replace(year=today.year - 1, month=1, day=1).isoformat(),
            'to': today.replace(year=today.year - 1, month=12, day=31).isoformat(),
        },
    }
    
    # Get common timezones
    common_timezones = [
        ('UTC', 'UTC (Coordinated Universal Time)'),
        ('America/New_York', 'Eastern Time (ET)'),
        ('America/Chicago', 'Central Time (CT)'),
        ('America/Denver', 'Mountain Time (MT)'),
        ('America/Los_Angeles', 'Pacific Time (PT)'),
        ('Europe/London', 'London (GMT)'),
        ('Europe/Paris', 'Paris (CET)'),
        ('Asia/Tokyo', 'Tokyo (JST)'),
        ('Asia/Shanghai', 'Shanghai (CST)'),
        ('Australia/Sydney', 'Sydney (AEST)'),
    ]
    
    # Get user's current preferences (Phase 2: Load from user profile)
    default_date_range = request.GET.get('default_date_range', '30')
    default_compare_period = request.GET.get('default_compare_period', 'previous')
    timezone = request.GET.get('timezone', 'UTC')
    
    context = {
        'presets': presets,
        'common_timezones': common_timezones,
        'default_date_range': default_date_range,
        'default_compare_period': default_compare_period,
        'timezone': timezone,
        'today': today.isoformat(),
    }
    
    return render(request, 'core/analytics_date_filters.html', context)


@login_required
def inventory_overview(request):
    """
    Main inventory overview page showing inventory summary, alerts, health metrics, and quick access to inventory sub-pages.
    """
    from apps.accounts.models import Organization
    from apps.amazon_auth.models import AmazonAccount
    from apps.amazon_sp.models import Product, Inventory as SPInventory
    from apps.inventory.models import InventoryAlert, AutoPauseRule
    from apps.amazon_ads.models import Campaign
    from django.db.models import Sum, Count, Q, Max
    from datetime import datetime, timedelta
    from decimal import Decimal
    
    # Get user's organizations
    user_organizations = Organization.objects.filter(
        Q(owner=request.user) | Q(members=request.user)
    ).distinct()
    
    # Get connected Amazon accounts
    amazon_accounts = AmazonAccount.objects.filter(
        organization__in=user_organizations,
        is_connected=True
    )
    
    # Get products for connected accounts
    products = Product.objects.filter(account__in=amazon_accounts)
    
    # Get today's date
    today = datetime.now().date()
    
    # Get latest inventory for each product
    # Get all inventory records and find latest per product
    all_inventory = SPInventory.objects.filter(
        product__in=products,
        date__lte=today
    ).select_related('product').order_by('product', '-date')
    
    # Group by product and get latest
    latest_inventory_dict = {}
    for inv in all_inventory:
        if inv.product_id not in latest_inventory_dict:
            latest_inventory_dict[inv.product_id] = inv
    
    latest_inventory = list(latest_inventory_dict.values())
    
    # Calculate summary statistics
    total_products = products.count()
    
    # Get products with active campaigns (through keywords/ad groups)
    # Note: Products don't have direct campaign relationship, so we'll use a placeholder
    # Phase 4: Implement proper product-campaign relationship tracking
    products_with_campaigns = 0  # Placeholder - will be calculated in Phase 4
    
    # Count low stock products
    low_stock_products = len([inv for inv in latest_inventory if inv.is_low_stock])
    
    # Count out of stock products (0 available)
    out_of_stock_products = len([
        inv for inv in latest_inventory 
        if (inv.available_quantity or 0) == 0 and (inv.fba_available or 0) == 0
    ])
    
    # Get paused campaigns due to inventory
    paused_campaigns = Campaign.objects.filter(
        account__in=amazon_accounts,
        state='paused'
    ).count()
    
    # Get active inventory alerts
    active_alerts = InventoryAlert.objects.filter(
        account__in=amazon_accounts,
        status='active'
    )
    
    low_stock_alerts_count = active_alerts.filter(alert_type='low_stock').count()
    out_of_stock_alerts_count = active_alerts.filter(alert_type='out_of_stock').count()
    
    # Calculate FBA vs FBM distribution
    fba_products = len([inv for inv in latest_inventory if (inv.fba_available or 0) > 0])
    fbm_products = len([
        inv for inv in latest_inventory 
        if (inv.fba_available or 0) == 0 and (inv.available_quantity or 0) > 0
    ])
    
    # Calculate inventory health score (0-100)
    # Based on: low stock ratio, out of stock ratio, alert ratio
    if total_products > 0:
        low_stock_ratio = (low_stock_products / total_products) * 100
        out_of_stock_ratio = (out_of_stock_products / total_products) * 100
        alert_ratio = (active_alerts.count() / total_products) * 100
        
        # Health score: 100 - (penalties)
        health_score = max(0, 100 - (low_stock_ratio * 0.3) - (out_of_stock_ratio * 0.5) - (alert_ratio * 0.2))
        health_score = int(health_score)
    else:
        health_score = 0
    
    # Get products needing attention
    products_needing_attention = []
    for inv in latest_inventory[:10]:  # Limit to 10
        total_available = inv.calculate_total_available()
        if inv.is_low_stock or total_available == 0:
            products_needing_attention.append({
                'product': inv.product,
                'available': total_available,
                'is_low_stock': inv.is_low_stock,
                'is_out_of_stock': total_available == 0,
                'threshold': inv.low_stock_threshold,
            })
    
    # Get recently restocked products (products that had alerts resolved in last 7 days)
    recently_restocked = InventoryAlert.objects.filter(
        account__in=amazon_accounts,
        alert_type='restocked',
        resolved_at__gte=today - timedelta(days=7)
    ).select_related('product')[:5]
    
    # Get auto-paused campaigns
    auto_paused_campaigns = Campaign.objects.filter(
        account__in=amazon_accounts,
        state='paused',
        inventory_pause_alerts__isnull=False
    ).distinct()[:5]
    
    # Get recent alerts (last 10)
    recent_alerts = active_alerts.select_related('product', 'account').order_by('-created_at')[:10]
    
    # Calculate inventory trends (last 30 days)
    inventory_trends = []
    for i in range(30):
        date = today - timedelta(days=29-i)
        date_inventory = SPInventory.objects.filter(
            product__in=products,
            date=date
        )
        
        total_available = date_inventory.aggregate(
            total=Sum('available_quantity') + Sum('fba_available')
        )['total'] or 0
        
        low_stock_count = date_inventory.filter(is_low_stock=True).count()
        out_of_stock_count = date_inventory.filter(
            Q(available_quantity=0, fba_available=0)
        ).count()
        
        inventory_trends.append({
            'date': date.isoformat(),
            'total_available': int(total_available),
            'low_stock_count': low_stock_count,
            'out_of_stock_count': out_of_stock_count,
        })
    
    # Get max values for chart scaling
    max_available = max([t['total_available'] for t in inventory_trends]) if inventory_trends else 1
    max_alerts = max([t['low_stock_count'] + t['out_of_stock_count'] for t in inventory_trends]) if inventory_trends else 1
    
    # Get products by status
    healthy_products = len([
        inv for inv in latest_inventory 
        if not inv.is_low_stock and (inv.available_quantity or 0) > 0
    ])
    
    context = {
        'amazon_accounts': amazon_accounts,
        'total_products': total_products,
        'products_with_campaigns': products_with_campaigns,
        'low_stock_products': low_stock_products,
        'out_of_stock_products': out_of_stock_products,
        'paused_campaigns': paused_campaigns,
        'low_stock_alerts_count': low_stock_alerts_count,
        'out_of_stock_alerts_count': out_of_stock_alerts_count,
        'fba_products': fba_products,
        'fbm_products': fbm_products,
        'health_score': health_score,
        'products_needing_attention': products_needing_attention,
        'recently_restocked': recently_restocked,
        'auto_paused_campaigns': auto_paused_campaigns,
        'recent_alerts': recent_alerts,
        'inventory_trends': inventory_trends,
        'max_available': max_available,
        'max_alerts': max_alerts,
        'healthy_products': healthy_products,
    }
    
    return render(request, 'core/inventory.html', context)


@login_required
def inventory_stock_levels(request):
    """
    Stock levels monitoring page: product inventory list, stock indicators, FBA/FBM status,
    inventory history, low stock warnings, and sync with Amazon SP-API.
    """
    from apps.accounts.models import Organization
    from apps.amazon_auth.models import AmazonAccount
    from apps.amazon_sp.models import Product, Inventory as SPInventory
    from django.db.models import Q, Sum
    from datetime import datetime, timedelta

    user_organizations = Organization.objects.filter(
        Q(owner=request.user) | Q(members=request.user)
    ).distinct()
    amazon_accounts = AmazonAccount.objects.filter(
        organization__in=user_organizations,
        is_connected=True
    )
    products = Product.objects.filter(account__in=amazon_accounts)
    today = datetime.now().date()

    # Latest inventory per product
    all_inventory = SPInventory.objects.filter(
        product__in=products,
        date__lte=today
    ).select_related('product').order_by('product', '-date')
    latest_inventory_dict = {}
    for inv in all_inventory:
        if inv.product_id not in latest_inventory_dict:
            latest_inventory_dict[inv.product_id] = inv
    latest_inventory = list(latest_inventory_dict.values())

    # Product list with status and FBA/FBM
    product_list = []
    for inv in latest_inventory:
        total = inv.calculate_total_available()
        if total == 0:
            status = 'out_of_stock'
        elif inv.is_low_stock:
            status = 'low_stock'
        else:
            status = 'healthy'
        is_fba = (inv.fba_available or 0) > 0
        is_fbm = (inv.available_quantity or 0) > 0
        fulfillment = 'FBA' if is_fba else ('FBM' if is_fbm else '—')
        product_list.append({
            'product': inv.product,
            'inv': inv,
            'total_available': total,
            'status': status,
            'fulfillment': fulfillment,
            'threshold': inv.low_stock_threshold,
        })

    # Sort: out of stock first, then low stock, then healthy
    order_key = {'out_of_stock': 0, 'low_stock': 1, 'healthy': 2}
    product_list.sort(key=lambda x: (order_key[x['status']], -x['total_available']))

    # Inventory history: last 14 days of snapshots (per day totals or recent records)
    history_days = 14
    inventory_history = []
    for i in range(history_days):
        d = today - timedelta(days=history_days - 1 - i)
        day_inv = SPInventory.objects.filter(
            product__in=products,
            date=d
        )
        total_avail = day_inv.aggregate(
            t=Sum('available_quantity')
        )['t'] or 0
        total_fba = day_inv.aggregate(
            t=Sum('fba_available')
        )['t'] or 0
        inventory_history.append({
            'date': d,
            'total_available': (total_avail or 0) + (total_fba or 0),
            'low_stock_count': day_inv.filter(is_low_stock=True).count(),
            'out_of_stock_count': day_inv.filter(
                Q(available_quantity=0, fba_available=0)
            ).count(),
        })

    # Low stock warnings (products that are low or out of stock)
    low_stock_warnings = [p for p in product_list if p['status'] in ('low_stock', 'out_of_stock')]
    healthy_count = len([p for p in product_list if p['status'] == 'healthy'])
    max_history_available = max([h['total_available'] for h in inventory_history]) or 1

    context = {
        'product_list': product_list,
        'inventory_history': inventory_history,
        'low_stock_warnings': low_stock_warnings,
        'total_products': len(product_list),
        'healthy_count': healthy_count,
        'max_history_available': max_history_available,
    }
    return render(request, 'core/stock_levels.html', context)


@login_required
def inventory_low_inventory_warnings(request):
    """
    Low inventory warnings/alerts page: low stock alerts list, alert thresholds,
    auto-pause rules for out-of-stock, notification settings, and alert history.
    """
    from apps.accounts.models import Organization
    from apps.amazon_auth.models import AmazonAccount
    from apps.inventory.models import InventoryAlert, AutoPauseRule
    from apps.notifications.models import NotificationPreference
    from django.db.models import Q

    user_organizations = Organization.objects.filter(
        Q(owner=request.user) | Q(members=request.user)
    ).distinct()
    amazon_accounts = AmazonAccount.objects.filter(
        organization__in=user_organizations,
        is_connected=True
    )

    # Low stock alerts list (active low_stock and out_of_stock)
    low_stock_alerts = InventoryAlert.objects.filter(
        account__in=amazon_accounts,
        status='active',
        alert_type__in=('low_stock', 'out_of_stock')
    ).select_related('product', 'account').order_by('-created_at')[:100]

    # Auto-pause rules for out-of-stock
    auto_pause_rules = AutoPauseRule.objects.filter(
        account__in=amazon_accounts
    ).prefetch_related('products', 'campaigns').order_by('-updated_at')

    # Notification settings (preferences for low inventory)
    notification_prefs, _ = NotificationPreference.objects.get_or_create(
        user=request.user,
        defaults={
            'email_low_inventory': True,
            'in_app_low_inventory': True,
        }
    )

    # Alert history (all alert types, recent first)
    alert_history = InventoryAlert.objects.filter(
        account__in=amazon_accounts
    ).select_related('product', 'account').order_by('-created_at')[:50]

    # Default threshold used in inventory (display only; config via auto-pause rules)
    default_low_stock_threshold = 10

    context = {
        'low_stock_alerts': low_stock_alerts,
        'auto_pause_rules': auto_pause_rules,
        'notification_prefs': notification_prefs,
        'alert_history': alert_history,
        'default_low_stock_threshold': default_low_stock_threshold,
        'amazon_accounts': amazon_accounts,
    }
    return render(request, 'core/low_inventory_warnings.html', context)


@login_required
def inventory_paused_campaigns(request):
    """
    Paused campaigns page: campaigns paused due to inventory, pause reason,
    resume when stock available, auto-resume settings, and manual resume.
    """
    from apps.accounts.models import Organization
    from apps.amazon_auth.models import AmazonAccount
    from apps.amazon_ads.models import Campaign
    from apps.inventory.models import InventoryAlert, AutoPauseRule
    from django.db.models import Q
    from django.shortcuts import get_object_or_404, redirect

    user_organizations = Organization.objects.filter(
        Q(owner=request.user) | Q(members=request.user)
    ).distinct()
    amazon_accounts = AmazonAccount.objects.filter(
        organization__in=user_organizations,
        is_connected=True
    )

    # POST: manual resume one campaign
    if request.method == 'POST' and request.POST.get('action') == 'resume':
        campaign_id = request.POST.get('campaign_id')
        if campaign_id:
            campaign = get_object_or_404(
                Campaign,
                id=campaign_id,
                account__in=amazon_accounts,
                state='paused'
            )
            campaign.state = 'enabled'
            campaign.save()
            from django.contrib import messages
            messages.success(request, f'Campaign "{campaign.name}" resumed successfully.')
        return redirect('inventory_paused_campaigns')

    # Campaigns paused due to inventory (linked to at least one inventory alert)
    paused_qs = Campaign.objects.filter(
        account__in=amazon_accounts,
        state='paused',
        inventory_pause_alerts__isnull=False
    ).distinct().select_related('account').prefetch_related(
        'inventory_pause_alerts__product',
        'inventory_pause_alerts__account',
        'auto_pause_rules',
    )

    # Build list with pause reason and auto-resume info
    paused_list = []
    for campaign in paused_qs:
        alerts = list(campaign.inventory_pause_alerts.all())
        has_out_of_stock = any(a.alert_type == 'out_of_stock' for a in alerts)
        pause_reason = 'out_of_stock' if has_out_of_stock else 'low_stock'
        rules = list(campaign.auto_pause_rules.filter(is_active=True))
        auto_resume = any(r.auto_resume for r in rules)
        resume_threshold = next((r.resume_threshold for r in rules if r.auto_resume), None)
        paused_list.append({
            'campaign': campaign,
            'pause_reason': pause_reason,
            'alerts': alerts,
            'auto_pause_rules': rules,
            'auto_resume': auto_resume,
            'resume_threshold': resume_threshold,
        })

    # Auto-resume settings (rules that apply to inventory-based pausing)
    auto_pause_rules = AutoPauseRule.objects.filter(
        account__in=amazon_accounts,
        is_active=True
    ).prefetch_related('campaigns', 'products').order_by('name')

    auto_resume_count = sum(1 for p in paused_list if p['auto_resume'])

    context = {
        'paused_list': paused_list,
        'auto_pause_rules': auto_pause_rules,
        'auto_resume_count': auto_resume_count,
        'amazon_accounts': amazon_accounts,
    }
    return render(request, 'core/paused_campaigns.html', context)


@login_required
def alerts_overview(request):
    """
    Central alerts hub: spend, inventory, rule conflicts, and recent notifications.
    AiHello-inspired: stay up-to-date, actionable (why bids changed, when to restock).
    """
    from apps.accounts.models import Organization
    from apps.amazon_auth.models import AmazonAccount
    from apps.inventory.models import InventoryAlert
    from apps.notifications.models import Notification
    from django.db.models import Q
    from datetime import datetime

    user_organizations = Organization.objects.filter(
        Q(owner=request.user) | Q(members=request.user)
    ).distinct()
    amazon_accounts = AmazonAccount.objects.filter(
        organization__in=user_organizations,
        is_connected=True
    )

    # Counts by category
    low_inventory_count = InventoryAlert.objects.filter(
        account__in=amazon_accounts,
        status='active',
        alert_type__in=('low_stock', 'out_of_stock')
    ).count()
    spend_spike_count = 0  # Computed on spend-spikes page; hub shows 0 or could be synced later
    # Rule conflicts count (same detection as rule-conflicts page: count conflicting pairs)
    from apps.autopilot.models import AutopilotGoal
    _goals = AutopilotGoal.objects.filter(account__in=amazon_accounts, is_active=True).prefetch_related('rules')
    _conflict_pairs = (
        ('keyword_pause', 'keyword_enable'), ('keyword_enable', 'keyword_pause'),
        ('campaign_pause', 'campaign_budget'), ('campaign_budget', 'campaign_pause'),
    )
    rule_conflicts_count = 0
    for _g in _goals:
        _rules = list(_g.rules.filter(is_active=True).values_list('rule_type', 'action_percentage'))
        _types = {r[0] for r in _rules}
        for _t1, _t2 in _conflict_pairs:
            if _t1 in _types and _t2 in _types:
                rule_conflicts_count += 1
                break
        if not any((_t1 in _types and _t2 in _types) for _t1, _t2 in _conflict_pairs):
            _bid_pcts = [r[1] for r in _rules if r[0] == 'keyword_bid']
            if _bid_pcts and any((b or 0) > 0 for b in _bid_pcts) and any((b or 0) < 0 for b in _bid_pcts):
                rule_conflicts_count += 1
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()

    # Recent in-app notifications
    recent_notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')[:15]

    # Recent inventory alerts (for feed)
    recent_inventory_alerts = InventoryAlert.objects.filter(
        account__in=amazon_accounts
    ).select_related('product', 'account').order_by('-created_at')[:10]

    # Combined recent alerts feed (notifications + inventory), sorted by date
    recent_alerts = []
    for n in recent_notifications:
        recent_alerts.append({
            'type': 'notification',
            'badge': n.type,
            'title': n.title,
            'message': n.message,
            'created_at': n.created_at,
            'link': '',
            'is_read': n.is_read,
        })
    for a in recent_inventory_alerts:
        recent_alerts.append({
            'type': 'inventory',
            'badge': 'warning' if a.alert_type == 'low_stock' else ('error' if a.alert_type == 'out_of_stock' else 'success'),
            'title': a.get_alert_type_display(),
            'message': f"{a.product.asin} — {a.current_stock} units (threshold {a.threshold})" if a.message else f"{a.product.asin} — current: {a.current_stock}, threshold: {a.threshold}",
            'created_at': a.created_at,
            'link': '/inventory/low-inventory-warnings/',
            'is_read': False,
        })
    recent_alerts.sort(key=lambda x: x['created_at'], reverse=True)
    recent_alerts = recent_alerts[:20]

    context = {
        'spend_spike_count': spend_spike_count,
        'low_inventory_count': low_inventory_count,
        'rule_conflicts_count': rule_conflicts_count,
        'unread_count': unread_count,
        'recent_alerts': recent_alerts,
    }
    return render(request, 'core/alerts.html', context)


@login_required
def alerts_spend_spikes(request):
    """
    Spend spikes alerts page: unusual spending patterns, thresholds,
    notifications, historical spikes, and action recommendations.
    """
    from apps.accounts.models import Organization
    from apps.amazon_auth.models import AmazonAccount
    from apps.amazon_ads.models import CampaignPerformance
    from apps.notifications.models import NotificationPreference
    from django.db.models import Q, Sum
    from datetime import datetime, timedelta
    from decimal import Decimal

    user_organizations = Organization.objects.filter(
        Q(owner=request.user) | Q(members=request.user)
    ).distinct()
    amazon_accounts = AmazonAccount.objects.filter(
        organization__in=user_organizations,
        is_connected=True
    )

    # Daily spend (last 31 days) for spike detection
    today = datetime.now().date()
    start_date = today - timedelta(days=31)
    daily_totals = (
        CampaignPerformance.objects.filter(
            campaign__account__in=amazon_accounts,
            date__gte=start_date,
            date__lte=today,
        )
        .values('date')
        .annotate(total=Sum('cost'))
        .order_by('date')
    )
    daily_spend_map = {item['date']: float(item['total'] or 0) for item in daily_totals}

    # Spike detection: day-over-day increase above threshold (default 50%)
    spike_threshold_pct = 50
    min_spend_to_alert = 10.0  # ignore tiny spikes below $10
    spend_spike_alerts = []
    historical_spikes = []
    dates_sorted = sorted(daily_spend_map.keys())
    for i in range(1, len(dates_sorted)):
        d = dates_sorted[i]
        prev_d = dates_sorted[i - 1]
        spend = daily_spend_map[d]
        prev_spend = daily_spend_map.get(prev_d) or 0
        if prev_spend <= 0:
            continue
        change_pct = ((spend - prev_spend) / float(prev_spend)) * 100
        if change_pct >= spike_threshold_pct and spend >= min_spend_to_alert:
            entry = {
                'date': d,
                'spend': spend,
                'previous_spend': prev_spend,
                'change_pct': round(change_pct, 1),
                'campaign_name': None,
            }
            historical_spikes.append(entry)
            # Recent spikes (last 7 days) as "active" alerts
            if (today - d).days <= 7:
                spend_spike_alerts.append(entry)
    historical_spikes.sort(key=lambda x: x['date'], reverse=True)
    historical_spikes = historical_spikes[:30]

    # Notification preferences for spend alerts
    notification_prefs, _ = NotificationPreference.objects.get_or_create(
        user=request.user,
        defaults={'email_spend_alerts': True, 'in_app_spend_alerts': True},
    )

    # Default thresholds (display / future config)
    thresholds = {
        'spike_percent': spike_threshold_pct,
        'min_spend': min_spend_to_alert,
    }

    # Action recommendations (static + optional from spike severity)
    action_recommendations = [
        {'title': 'Review campaign budgets', 'description': 'Check daily budget limits on campaigns that drove the spike.', 'priority': 'high'},
        {'title': 'Check for runaway keywords', 'description': 'Identify keywords with unusually high spend and consider lowering bids or adding negatives.', 'priority': 'high'},
        {'title': 'Enable budget caps', 'description': 'Use Safety Controls to set max daily spend change limits per account.', 'priority': 'medium'},
        {'title': 'Compare to target ACOS', 'description': 'Ensure spike days did not push ACOS above your target.', 'priority': 'medium'},
    ]
    if spend_spike_alerts:
        action_recommendations.insert(0, {'title': 'Review recent spike days', 'description': 'Drill into the dates listed above and adjust bids or budgets as needed.', 'priority': 'high'})

    context = {
        'spend_spike_alerts': spend_spike_alerts,
        'historical_spikes': historical_spikes,
        'thresholds': thresholds,
        'notification_prefs': notification_prefs,
        'action_recommendations': action_recommendations,
    }
    return render(request, 'core/spend_spikes.html', context)


@login_required
def alerts_rule_conflicts(request):
    """
    Rule conflicts alerts page: when autopilot rules conflict with each other.
    Features: conflict detection, conflicting rules list, resolution suggestions,
    conflict history, auto-resolution options.
    """
    from apps.accounts.models import Organization
    from apps.amazon_auth.models import AmazonAccount
    from apps.autopilot.models import AutopilotGoal, AutomationRule
    from django.db.models import Q

    user_organizations = Organization.objects.filter(
        Q(owner=request.user) | Q(members=request.user)
    ).distinct()
    amazon_accounts = AmazonAccount.objects.filter(
        organization__in=user_organizations,
        is_connected=True
    )

    goals = AutopilotGoal.objects.filter(
        account__in=amazon_accounts,
        is_active=True
    ).prefetch_related('rules')
    rules_by_goal = {}
    for g in goals:
        rules_by_goal[g.id] = list(g.rules.filter(is_active=True).order_by('-priority'))

    # Conflict detection: same goal, opposite or overlapping rule types
    conflicting_rules_list = []
    conflict_types = {
        ('keyword_pause', 'keyword_enable'): 'Opposite keyword actions (pause vs enable)',
        ('keyword_enable', 'keyword_pause'): 'Opposite keyword actions (enable vs pause)',
        ('campaign_pause', 'campaign_budget'): 'Campaign pause conflicts with budget adjustment',
        ('campaign_budget', 'campaign_pause'): 'Budget adjustment conflicts with campaign pause',
    }
    for goal in goals:
        rules = rules_by_goal.get(goal.id, [])
        for i in range(len(rules)):
            for j in range(i + 1, len(rules)):
                r1, r2 = rules[i], rules[j]
                key = (r1.rule_type, r2.rule_type)
                if key in conflict_types:
                    conflicting_rules_list.append({
                        'rule_a': r1,
                        'rule_b': r2,
                        'goal': goal,
                        'conflict_type': conflict_types[key],
                        'reason': f"Both rules apply to the same goal scope; one may undo the other's action.",
                    })
                elif r1.rule_type == r2.rule_type == 'keyword_bid':
                    if (r1.action_percentage or 0) * (r2.action_percentage or 0) < 0:
                        conflicting_rules_list.append({
                            'rule_a': r1,
                            'rule_b': r2,
                            'goal': goal,
                            'conflict_type': 'Opposite bid directions',
                            'reason': f"One rule increases bids, the other decreases; outcome depends on execution order.",
                        })

    # Resolution suggestions
    resolution_suggestions = [
        {'title': 'Adjust rule priorities', 'description': 'Set a clear priority order so one rule runs first. Higher priority rules execute before lower priority.', 'action': 'Go to Rules Engine'},
        {'title': 'Disable one of the conflicting rules', 'description': 'Temporarily turn off one rule until you decide which behavior you want.', 'action': 'Go to Rules Engine'},
        {'title': 'Narrow campaign or keyword scope', 'description': 'Apply each rule to different campaigns or ad groups so they do not target the same entities.', 'action': 'Edit goals / rules'},
        {'title': 'Combine logic into a single rule', 'description': 'If both conditions are valid, consider one rule with compound conditions instead of two.', 'action': 'Rules Engine'},
    ]

    # Conflict history (placeholder: no persisted history model yet)
    conflict_history = []

    # Auto-resolution options (display only; Phase 4 for persistence)
    auto_resolution_options = [
        {'id': 'prefer_priority', 'label': 'Prefer higher priority rule', 'description': 'When conflict is detected, only the higher-priority rule runs.', 'enabled': True},
        {'id': 'pause_lower', 'label': 'Pause lower-priority rule on conflict', 'description': 'Automatically pause the lower-priority rule until you resolve manually.', 'enabled': False},
        {'id': 'notify_only', 'label': 'Notify only (no auto-resolution)', 'description': 'Alert you to conflicts but do not change rule execution.', 'enabled': False},
    ]

    context = {
        'conflicting_rules_list': conflicting_rules_list,
        'resolution_suggestions': resolution_suggestions,
        'conflict_history': conflict_history,
        'auto_resolution_options': auto_resolution_options,
        'goals': goals,
    }
    return render(request, 'core/rule_conflicts.html', context)


@login_required
def settings_amazon_accounts(request):
    """
    Amazon accounts management: connect and manage Amazon Advertising and SP-API accounts.
    Connected list, connect (OAuth placeholder), disconnect, account status, token refresh, permissions.
    Ready for API keys later; OAuth flow not implemented yet.
    """
    from apps.accounts.models import Organization
    from apps.amazon_auth.models import AmazonAccount, AmazonAdsAuth, AmazonSPAuth
    from django.db.models import Q
    from django.shortcuts import get_object_or_404, redirect
    from django.contrib import messages
    from django.utils import timezone

    user_organizations = Organization.objects.filter(
        Q(owner=request.user) | Q(members=request.user)
    ).distinct()
    accounts_qs = AmazonAccount.objects.filter(
        organization__in=user_organizations
    ).select_related('organization').order_by('-created_at')

    # POST: disconnect or refresh (placeholder)
    if request.method == 'POST':
        action = request.POST.get('action')
        account_id = request.POST.get('account_id')
        if not account_id:
            messages.error(request, 'No account specified.')
            return redirect('settings_amazon_accounts')
        account = get_object_or_404(
            AmazonAccount,
            id=account_id,
            organization__in=user_organizations,
        )
        if action == 'disconnect':
            account.is_connected = False
            account.save()
            messages.success(request, f'Account "{account.account_name}" has been disconnected.')
            return redirect('settings_amazon_accounts')
        if action == 'refresh':
            messages.info(request, 'Token refresh will be available when API keys are configured.')
            return redirect('settings_amazon_accounts')

    # Build account list with status and token info
    account_list = []
    for acc in accounts_qs:
        has_ads = hasattr(acc, 'ads_auth') and acc.ads_auth is not None
        has_sp = hasattr(acc, 'sp_auth') and acc.sp_auth is not None
        ads_status = None
        sp_status = None
        ads_expires = None
        sp_expires = None
        if has_ads:
            try:
                ads_expires = acc.ads_auth.expires_at
                ads_status = 'expired' if acc.ads_auth.is_token_expired() else ('refresh' if acc.ads_auth.needs_refresh() else 'ok')
            except Exception:
                ads_status = 'unknown'
        if has_sp:
            try:
                sp_expires = acc.sp_auth.expires_at
                sp_status = 'expired' if acc.sp_auth.is_token_expired() else ('refresh' if acc.sp_auth.needs_refresh() else 'ok')
            except Exception:
                sp_status = 'unknown'
        account_list.append({
            'account': acc,
            'has_ads': has_ads,
            'has_sp': has_sp,
            'ads_status': ads_status,
            'sp_status': sp_status,
            'ads_expires': ads_expires,
            'sp_expires': sp_expires,
        })

    context = {
        'account_list': account_list,
    }
    return render(request, 'core/amazon_accounts.html', context)


@login_required
def settings_team(request):
    """
    Team members management for multi-user workspaces.
    List members, invite, role management (Admin, Member, Viewer), remove, permission settings.
    """
    from apps.accounts.models import Organization, OrganizationMember
    from django.contrib.auth import get_user_model
    from django.db.models import Q
    from django.shortcuts import redirect
    from django.contrib import messages

    User = get_user_model()
    user_organizations = Organization.objects.filter(
        Q(owner=request.user) | Q(members=request.user)
    ).distinct()
    # If user has no organization (e.g. signed up via web and no org was created), create a default one
    if not user_organizations.exists():
        from django.utils.text import slugify
        base_slug = slugify(request.user.email.split('@')[0]) or 'workspace'
        slug = base_slug
        n = 0
        while Organization.objects.filter(slug=slug).exists():
            n += 1
            slug = f'{base_slug}-{request.user.id}' if n == 1 else f'{base_slug}-{n}'
        full_name = (request.user.get_full_name() or '').strip()
        name = full_name or request.user.email
        if not name or name == request.user.email:
            name = 'My Workspace'
        else:
            name = f"{name}'s Workspace"
        Organization.objects.create(name=name, slug=slug, owner=request.user)
        user_organizations = Organization.objects.filter(
            Q(owner=request.user) | Q(members=request.user)
        ).distinct()
    # Orgs the user can manage (owner or admin role)
    manageable_orgs = []
    for org in user_organizations:
        if org.owner_id == request.user.id:
            manageable_orgs.append(org)
        else:
            mem = OrganizationMember.objects.filter(organization=org, user=request.user).first()
            if mem and mem.role == 'admin':
                manageable_orgs.append(org)

    def team_redirect(org=None):
        if org:
            return redirect('/settings/team/?org=' + str(org.id))
        return redirect('settings_team')

    # POST: invite, remove, change_role
    if request.method == 'POST':
        action = request.POST.get('action')
        org_id = request.POST.get('organization_id')
        org = None
        if org_id:
            org = Organization.objects.filter(id=org_id, id__in=[o.id for o in manageable_orgs]).first()
        if action == 'invite' and org:
            email = (request.POST.get('email') or '').strip().lower()
            role = request.POST.get('role') or 'member'
            if role not in ('admin', 'member', 'viewer'):
                role = 'member'
            if not email:
                messages.error(request, 'Please enter an email address.')
            else:
                invite_user = User.objects.filter(email__iexact=email).first()
                if not invite_user:
                    messages.error(request, f'No user found with email "{email}". They must register first.')
                elif OrganizationMember.objects.filter(organization=org, user=invite_user).exists():
                    messages.error(request, f'{email} is already a member of this organization.')
                elif org.owner_id == invite_user.id:
                    messages.error(request, 'The owner is already part of the organization.')
                else:
                    OrganizationMember.objects.create(organization=org, user=invite_user, role=role)
                    messages.success(request, f'Invited {email} as {role}.')
            return team_redirect(org)
        if action == 'remove' and org:
            mid = request.POST.get('membership_id')
            if mid:
                membership = OrganizationMember.objects.filter(id=mid, organization=org).first()
                if membership:
                    email = membership.user.email
                    membership.delete()
                    messages.success(request, f'Removed {email} from the team.')
            return team_redirect(org)
        if action == 'change_role' and org:
            mid = request.POST.get('membership_id')
            new_role = (request.POST.get('role') or '').strip().lower()
            if mid and new_role in ('admin', 'member', 'viewer'):
                membership = OrganizationMember.objects.filter(id=mid, organization=org).first()
                if membership:
                    membership.role = new_role
                    membership.save()
                    messages.success(request, f'Role updated to {new_role}.')
            return team_redirect(org)

    # Selected org: from GET or first manageable
    org_id_param = request.GET.get('org')
    selected_org = None
    if org_id_param:
        selected_org = next((o for o in manageable_orgs if str(o.id) == str(org_id_param)), None)
    if not selected_org and manageable_orgs:
        selected_org = manageable_orgs[0]
    team_list = []
    if selected_org:
        owner_entry = {
            'user': selected_org.owner,
            'role': 'owner',
            'joined_at': None,
            'membership_id': None,
            'is_owner': True,
        }
        team_list.append(owner_entry)
        for m in OrganizationMember.objects.filter(organization=selected_org).select_related('user').order_by('joined_at'):
            team_list.append({
                'user': m.user,
                'role': m.role,
                'joined_at': m.joined_at,
                'membership_id': m.id,
                'is_owner': False,
            })

    role_choices = [('admin', 'Admin'), ('member', 'Member'), ('viewer', 'Viewer')]
    context = {
        'organizations': user_organizations,
        'manageable_orgs': manageable_orgs,
        'selected_org': selected_org,
        'team_list': team_list,
        'role_choices': role_choices,
    }
    return render(request, 'core/team.html', context)


# Default keys for autopilot preferences (used in settings_autopilot_preferences)
AUTOPILOT_PREF_DEFAULTS = {
    'default_autopilot_enabled': True,
    'default_lookback_days': 7,
    'max_bid_changes_per_day': 50,
    'max_budget_changes_per_day': 10,
    'max_campaign_pauses_per_day': 5,
    'max_daily_budget_increase_percent': 50,
    'max_daily_budget_decrease_percent': 30,
    'notify_email': True,
    'notify_in_app': True,
    'notify_high_impact_only': False,
    'require_approval_campaign_pause': True,
    'require_approval_budget_above_percent': 20,
    'default_goal_type': 'profit',
    'default_target_acos': None,
    'default_target_roas': None,
}


@login_required
def settings_autopilot_preferences(request):
    """
    Autopilot preferences configuration: default settings, global safety limits,
    notification preferences, action approval settings, default goals.
    """
    from apps.accounts.models import Organization
    from apps.autopilot.models import AutopilotPreference
    from django.db.models import Q

    user_organizations = Organization.objects.filter(
        Q(owner=request.user) | Q(members=request.user)
    ).distinct()
    if not user_organizations.exists():
        from django.utils.text import slugify
        base_slug = slugify(request.user.email.split('@')[0]) or 'workspace'
        slug = base_slug
        n = 0
        while Organization.objects.filter(slug=slug).exists():
            n += 1
            slug = f'{base_slug}-{request.user.id}' if n == 1 else f'{base_slug}-{n}'
        full_name = (request.user.get_full_name() or '').strip()
        name = full_name or request.user.email
        if not name or name == request.user.email:
            name = 'My Workspace'
        else:
            name = f"{name}'s Workspace"
        Organization.objects.create(name=name, slug=slug, owner=request.user)
        user_organizations = Organization.objects.filter(
            Q(owner=request.user) | Q(members=request.user)
        ).distinct()

    org_id_param = request.GET.get('org')
    selected_org = None
    if org_id_param:
        selected_org = user_organizations.filter(id=org_id_param).first()
    if not selected_org:
        selected_org = user_organizations.first()

    preference = None
    prefs = {}
    if selected_org:
        preference, _ = AutopilotPreference.objects.get_or_create(
            organization=selected_org,
            defaults={'settings': {}}
        )
        prefs = {**AUTOPILOT_PREF_DEFAULTS, **(preference.settings or {})}

    if request.method == 'POST':
        if preference and selected_org:
            s = preference.settings or {}
            s['default_autopilot_enabled'] = request.POST.get('default_autopilot_enabled') == 'on'
            try:
                s['default_lookback_days'] = int(request.POST.get('default_lookback_days') or 7)
            except ValueError:
                s['default_lookback_days'] = 7
            s['max_bid_changes_per_day'] = int(request.POST.get('max_bid_changes_per_day') or 50)
            s['max_budget_changes_per_day'] = int(request.POST.get('max_budget_changes_per_day') or 10)
            s['max_campaign_pauses_per_day'] = int(request.POST.get('max_campaign_pauses_per_day') or 5)
            try:
                s['max_daily_budget_increase_percent'] = float(request.POST.get('max_daily_budget_increase_percent') or 50)
            except ValueError:
                s['max_daily_budget_increase_percent'] = 50
            try:
                s['max_daily_budget_decrease_percent'] = float(request.POST.get('max_daily_budget_decrease_percent') or 30)
            except ValueError:
                s['max_daily_budget_decrease_percent'] = 30
            s['notify_email'] = request.POST.get('notify_email') == 'on'
            s['notify_in_app'] = request.POST.get('notify_in_app') == 'on'
            s['notify_high_impact_only'] = request.POST.get('notify_high_impact_only') == 'on'
            s['require_approval_campaign_pause'] = request.POST.get('require_approval_campaign_pause') == 'on'
            try:
                s['require_approval_budget_above_percent'] = float(request.POST.get('require_approval_budget_above_percent') or 20)
            except ValueError:
                s['require_approval_budget_above_percent'] = 20
            goal_type = request.POST.get('default_goal_type') or 'profit'
            if goal_type in ('profit', 'growth', 'rank', 'acos', 'roas'):
                s['default_goal_type'] = goal_type
            try:
                acos_val = request.POST.get('default_target_acos')
                s['default_target_acos'] = float(acos_val) if acos_val not in (None, '') else None
            except ValueError:
                s['default_target_acos'] = None
            try:
                roas_val = request.POST.get('default_target_roas')
                s['default_target_roas'] = float(roas_val) if roas_val not in (None, '') else None
            except ValueError:
                s['default_target_roas'] = None
            preference.settings = s
            preference.save()
            messages.success(request, 'Autopilot preferences saved.')
        return redirect(request.path + ('?org=' + str(selected_org.id) if selected_org else ''))

    goal_type_choices = [
        ('profit', 'Maximize Profit'),
        ('growth', 'Maximize Growth'),
        ('rank', 'Improve Ranking'),
        ('acos', 'Target ACOS'),
        ('roas', 'Target ROAS'),
    ]
    context = {
        'selected_org': selected_org,
        'organizations': user_organizations,
        'prefs': prefs,
        'goal_type_choices': goal_type_choices,
    }
    return render(request, 'core/autopilot_preferences.html', context)


@login_required
def settings_notifications(request):
    """
    Notification preferences: email and in-app settings, notification types,
    frequency, and notification history.
    """
    from apps.notifications.models import NotificationPreference, Notification

    pref, _ = NotificationPreference.objects.get_or_create(
        user=request.user,
        defaults={
            'email_autopilot_actions': True,
            'email_low_inventory': True,
            'email_spend_alerts': True,
            'email_daily_summary': False,
            'in_app_autopilot_actions': True,
            'in_app_low_inventory': True,
            'in_app_spend_alerts': True,
        }
    )

    if request.method == 'POST':
        pref.email_autopilot_actions = request.POST.get('email_autopilot_actions') == 'on'
        pref.email_low_inventory = request.POST.get('email_low_inventory') == 'on'
        pref.email_spend_alerts = request.POST.get('email_spend_alerts') == 'on'
        pref.email_daily_summary = request.POST.get('email_daily_summary') == 'on'
        pref.in_app_autopilot_actions = request.POST.get('in_app_autopilot_actions') == 'on'
        pref.in_app_low_inventory = request.POST.get('in_app_low_inventory') == 'on'
        pref.in_app_spend_alerts = request.POST.get('in_app_spend_alerts') == 'on'
        pref.save()
        messages.success(request, 'Notification preferences saved.')
        return redirect('settings_notifications')

    history = Notification.objects.filter(user=request.user).order_by('-created_at')[:50]

    context = {
        'pref': pref,
        'history': history,
    }
    return render(request, 'core/notifications_settings.html', context)


@login_required
def settings_billing(request):
    """
    Billing and subscription management (Phase 5 - Stripe).
    Current plan, upgrade/downgrade, payment methods, billing history, invoice download, usage limits.
    """
    from apps.accounts.models import Organization
    from apps.billing.models import (
        SubscriptionPlan,
        Subscription,
        PaymentMethod,
        Invoice,
        UsageRecord,
    )
    from django.db.models import Q

    user_organizations = Organization.objects.filter(
        Q(owner=request.user) | Q(members=request.user)
    ).distinct()
    if not user_organizations.exists():
        from django.utils.text import slugify
        base_slug = slugify(request.user.email.split('@')[0]) or 'workspace'
        slug = base_slug
        n = 0
        while Organization.objects.filter(slug=slug).exists():
            n += 1
            slug = f'{base_slug}-{request.user.id}' if n == 1 else f'{base_slug}-{n}'
        full_name = (request.user.get_full_name() or '').strip()
        name = full_name or request.user.email
        if not name or name == request.user.email:
            name = 'My Workspace'
        else:
            name = f"{name}'s Workspace"
        Organization.objects.create(name=name, slug=slug, owner=request.user)
        user_organizations = Organization.objects.filter(
            Q(owner=request.user) | Q(members=request.user)
        ).distinct()

    org_id_param = request.GET.get('org')
    selected_org = user_organizations.filter(id=org_id_param).first() if org_id_param else None
    if not selected_org:
        selected_org = user_organizations.first()

    subscription = None
    plans = list(SubscriptionPlan.objects.filter(is_active=True).order_by('price_monthly'))
    payment_methods = []
    invoices = []
    usage = {}
    free_plan = None

    if selected_org:
        free_plan = SubscriptionPlan.objects.filter(plan_type='free').first()
        if not free_plan and plans:
            free_plan = plans[0]
        if not plans:
            free_plan = SubscriptionPlan.objects.create(
                name='Free',
                plan_type='free',
                price_monthly=0,
                max_accounts=1,
                max_campaigns=10,
            )
            plans = [free_plan]
        elif not free_plan:
            free_plan = plans[0]
        subscription, _ = Subscription.objects.get_or_create(
            organization=selected_org,
            defaults={
                'plan': free_plan,
                'status': 'trialing',
            }
        )
        if subscription and not subscription.plan_id:
            subscription.plan = free_plan
            subscription.save(update_fields=['plan'])
        payment_methods = list(PaymentMethod.objects.filter(organization=selected_org).order_by('-is_default', 'created_at'))
        invoices = list(Invoice.objects.filter(organization=selected_org)[:24])
        if subscription:
            latest_usage = UsageRecord.objects.filter(subscription=subscription).order_by('-date').first()
            if latest_usage:
                usage = {
                    'accounts_count': latest_usage.accounts_count,
                    'campaigns_count': latest_usage.campaigns_count,
                    'automation_runs': latest_usage.automation_runs,
                }
            else:
                from apps.amazon_auth.models import AmazonAccount
                from apps.autopilot.models import AutomationRule
                acc_count = AmazonAccount.objects.filter(organization=selected_org).count()
                usage = {
                    'accounts_count': acc_count,
                    'campaigns_count': 0,
                    'automation_runs': 0,
                }

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'change_plan' and selected_org and subscription:
            plan_id = request.POST.get('plan_id')
            new_plan = SubscriptionPlan.objects.filter(id=plan_id, is_active=True).first()
            if new_plan and new_plan.id != subscription.plan_id:
                subscription.plan = new_plan
                subscription.save(update_fields=['plan'])
                messages.success(request, f'Plan updated to {new_plan.name}. Stripe will sync when keys are configured.')
            return redirect(request.path + ('?org=' + str(selected_org.id) if selected_org else ''))
        if action == 'set_default_pm' and selected_org:
            pm_id = request.POST.get('payment_method_id')
            pm = PaymentMethod.objects.filter(id=pm_id, organization=selected_org).first()
            if pm:
                PaymentMethod.objects.filter(organization=selected_org).update(is_default=False)
                pm.is_default = True
                pm.save(update_fields=['is_default'])
                messages.success(request, 'Default payment method updated.')
            return redirect(request.path + ('?org=' + str(selected_org.id) if selected_org else ''))
        if action == 'download_invoice':
            inv_id = request.POST.get('invoice_id')
            inv = Invoice.objects.filter(id=inv_id).first()
            if inv and selected_org and inv.organization_id == selected_org.id and inv.invoice_pdf_url:
                return redirect(inv.invoice_pdf_url)
            if inv and selected_org and inv.organization_id == selected_org.id:
                messages.info(request, 'Invoice PDF will be available when Stripe is connected.')
            return redirect(request.path + ('?org=' + str(selected_org.id) if selected_org else ''))

    context = {
        'selected_org': selected_org,
        'organizations': user_organizations,
        'subscription': subscription,
        'plans': plans,
        'payment_methods': payment_methods,
        'invoices': invoices,
        'usage': usage,
    }
    return render(request, 'core/billing_settings.html', context)

