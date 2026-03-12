"""
URL configuration for Appca project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from apps.core.views import home, login_view, register_view, logout_view, dashboard, dashboard_overview, dashboard_spend, dashboard_sales, dashboard_acos, dashboard_autopilot_status, autopilot_overview, autopilot_goals, autopilot_rules_engine, autopilot_safety_controls, autopilot_change_history, advertising_overview, campaigns_list, sponsored_products_list, ad_groups_list, keywords_list, search_terms_list, negative_keywords_list, budgets_list, analytics_overview, analytics_performance_reports, analytics_keyword_performance, analytics_campaign_trends, analytics_date_filters, inventory_overview, inventory_stock_levels, inventory_low_inventory_warnings, inventory_paused_campaigns, alerts_overview, alerts_spend_spikes, alerts_rule_conflicts, password_reset_view, password_change_view, forgot_password_view

# Web Routes - must come first to catch root URL
urlpatterns = [
    path('', home, name='home'),
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', logout_view, name='logout'),
    path('password-reset/', password_reset_view, name='password_reset'),
    path('password-change/', password_change_view, name='password_change'),
    path('forgot-password/', forgot_password_view, name='forgot_password'),
    path('dashboard/', dashboard, name='dashboard'),
    path('dashboard/overview/', dashboard_overview, name='dashboard_overview'),
    path('dashboard/spend/', dashboard_spend, name='dashboard_spend'),
    path('dashboard/sales/', dashboard_sales, name='dashboard_sales'),
    path('dashboard/acos/', dashboard_acos, name='dashboard_acos'),
    path('dashboard/autopilot-status/', dashboard_autopilot_status, name='dashboard_autopilot_status'),
    path('autopilot/', autopilot_overview, name='autopilot_overview'),
    path('autopilot/goals/', autopilot_goals, name='autopilot_goals'),
    path('autopilot/rules-engine/', autopilot_rules_engine, name='autopilot_rules_engine'),
    path('autopilot/safety-controls/', autopilot_safety_controls, name='autopilot_safety_controls'),
    path('autopilot/change-history/', autopilot_change_history, name='autopilot_change_history'),
    path('advertising/', advertising_overview, name='advertising_overview'),
    path('advertising/campaigns/', campaigns_list, name='campaigns_list'),
    path('advertising/sponsored-products/', sponsored_products_list, name='sponsored_products_list'),
    path('advertising/ad-groups/', ad_groups_list, name='ad_groups_list'),
    path('advertising/keywords/', keywords_list, name='keywords_list'),
    path('advertising/search-terms/', search_terms_list, name='search_terms_list'),
    path('advertising/negative-keywords/', negative_keywords_list, name='negative_keywords_list'),
    path('advertising/budgets/', budgets_list, name='budgets_list'),
    path('analytics/', analytics_overview, name='analytics_overview'),
    path('analytics/performance-reports/', analytics_performance_reports, name='analytics_performance_reports'),
    path('analytics/keyword-performance/', analytics_keyword_performance, name='analytics_keyword_performance'),
    path('analytics/campaign-trends/', analytics_campaign_trends, name='analytics_campaign_trends'),
    path('analytics/date-filters/', analytics_date_filters, name='analytics_date_filters'),
    path('inventory/', inventory_overview, name='inventory_overview'),
    path('inventory/stock-levels/', inventory_stock_levels, name='inventory_stock_levels'),
    path('inventory/low-inventory-warnings/', inventory_low_inventory_warnings, name='inventory_low_inventory_warnings'),
    path('inventory/paused-campaigns/', inventory_paused_campaigns, name='inventory_paused_campaigns'),
    path('alerts/', alerts_overview, name='alerts_overview'),
    path('alerts/spend-spikes/', alerts_spend_spikes, name='alerts_spend_spikes'),
    path('alerts/rule-conflicts/', alerts_rule_conflicts, name='alerts_rule_conflicts'),
    path('settings/', include('config.settings_urls')),
    
    # Admin
    path('admin/', admin.site.urls),
    
    # API Routes
    path('api/auth/', include('apps.accounts.urls')),
    path('api/amazon/', include('apps.amazon_auth.urls')),
    path('api/ads/', include('apps.amazon_ads.urls')),
    path('api/sp/', include('apps.amazon_sp.urls')),
    path('api/autopilot/', include('apps.autopilot.urls')),
    path('api/analytics/', include('apps.analytics.urls')),
    path('api/inventory/', include('apps.inventory.urls')),
    path('api/notifications/', include('apps.notifications.urls')),
    path('api/billing/', include('apps.billing.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

