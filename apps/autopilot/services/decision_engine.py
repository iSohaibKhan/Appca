"""
Decision engine for Autopilot.
Evaluates rules and makes automation decisions.
"""
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from typing import Dict, List, Optional
from ..models import AutomationRule, AutopilotExecution, SafetyLimit
from apps.amazon_ads.models import Keyword, Campaign, KeywordPerformance


class DecisionEngine:
    """
    Core decision engine for rule-based automation.
    
    TODO: Phase 3 - Implement rule evaluation logic
    TODO: Phase 3 - Add safety checks
    TODO: Phase 4 - Add explainability features
    """
    
    def __init__(self, account):
        """
        Initialize decision engine for an account.
        """
        self.account = account
        self.safety_limits = SafetyLimit.objects.get_or_create(account=account)[0]
    
    def evaluate_rules(self, goal_id: Optional[int] = None):
        """
        Evaluate all active rules and generate execution plan.
        
        TODO: Phase 3 - Implement rule evaluation
        """
        from ..models import AutopilotGoal
        
        # Get active goals
        if goal_id:
            goals = AutopilotGoal.objects.filter(id=goal_id, is_active=True, account=self.account)
        else:
            goals = AutopilotGoal.objects.filter(is_active=True, account=self.account)
        
        executions = []
        
        for goal in goals:
            rules = AutomationRule.objects.filter(
                goal=goal,
                is_active=True
            ).order_by('-priority')
            
            for rule in rules:
                execution = self._evaluate_rule(rule)
                if execution:
                    executions.append(execution)
        
        return executions
    
    def _evaluate_rule(self, rule: AutomationRule) -> Optional[AutopilotExecution]:
        """
        Evaluate a single rule and create execution if condition is met.
        
        TODO: Phase 3 - Implement rule evaluation logic
        """
        # Check if safety limits allow execution
        if not self.safety_limits.is_enabled:
            return self._create_execution(
                rule,
                status='blocked',
                reason='Autopilot is disabled by safety limits',
                safety_check_passed=False
            )
        
        # Get entities to evaluate (keywords, campaigns, etc.)
        entities = self._get_entities_for_rule(rule)
        
        for entity in entities:
            # Get metrics for entity
            metrics = self._get_entity_metrics(entity, rule.lookback_days)
            
            # Check condition
            condition_met = self._check_condition(
                metrics.get(rule.condition_metric, 0),
                rule.condition_operator,
                rule.condition_value
            )
            
            if condition_met:
                # Calculate new value
                new_value = self._calculate_new_value(entity, rule, metrics)
                
                # Safety checks
                safety_passed, safety_reason = self._check_safety(entity, rule, new_value)
                
                if safety_passed:
                    return self._create_execution(
                        rule,
                        entity=entity,
                        condition_met=True,
                        metric_value=metrics.get(rule.condition_metric),
                        new_value=new_value,
                        reason=f"Condition met: {rule.condition_metric} {rule.condition_operator} {rule.condition_value}",
                        safety_check_passed=True
                    )
                else:
                    return self._create_execution(
                        rule,
                        entity=entity,
                        condition_met=True,
                        metric_value=metrics.get(rule.condition_metric),
                        status='blocked',
                        reason=f"Condition met but blocked by safety: {safety_reason}",
                        safety_check_passed=False,
                        safety_reason=safety_reason
                    )
        
        return None
    
    def _get_entities_for_rule(self, rule: AutomationRule) -> List:
        """
        Get entities (keywords, campaigns) to evaluate for a rule.
        
        TODO: Phase 3 - Implement entity selection
        """
        if rule.rule_type in ['keyword_bid', 'keyword_pause', 'keyword_enable']:
            # Get keywords from goal's campaigns
            campaigns = rule.goal.campaigns.all() if not rule.goal.applies_to_all_campaigns else Campaign.objects.filter(account=self.account)
            return Keyword.objects.filter(ad_group__campaign__in=campaigns, state='enabled')
        elif rule.rule_type in ['campaign_budget', 'campaign_pause']:
            campaigns = rule.goal.campaigns.all() if not rule.goal.applies_to_all_campaigns else Campaign.objects.filter(account=self.account)
            return list(campaigns)
        return []
    
    def _get_entity_metrics(self, entity, lookback_days: int) -> Dict:
        """
        Get performance metrics for an entity over lookback period.
        
        TODO: Phase 3 - Implement metrics aggregation
        """
        date_from = timezone.now().date() - timedelta(days=lookback_days)
        
        if isinstance(entity, Keyword):
            performances = KeywordPerformance.objects.filter(
                keyword=entity,
                date__gte=date_from
            )
            
            total_impressions = sum(p.impressions for p in performances)
            total_clicks = sum(p.clicks for p in performances)
            total_cost = sum(p.cost for p in performances)
            total_sales = sum(p.sales for p in performances)
            total_orders = sum(p.orders for p in performances)
            
            return {
                'impressions': total_impressions,
                'clicks': total_clicks,
                'cost': float(total_cost),
                'sales': float(total_sales),
                'orders': total_orders,
                'acos': float(entity.bid) if entity.bid else 0,  # Simplified
                'roas': float(total_sales / total_cost) if total_cost > 0 else 0,
                'ctr': float(total_clicks / total_impressions) if total_impressions > 0 else 0,
            }
        
        return {}
    
    def _check_condition(self, metric_value: float, operator: str, threshold: Decimal) -> bool:
        """
        Check if condition is met.
        
        TODO: Phase 3 - Implement condition checking
        """
        threshold_float = float(threshold)
        
        if operator == 'gt':
            return metric_value > threshold_float
        elif operator == 'gte':
            return metric_value >= threshold_float
        elif operator == 'lt':
            return metric_value < threshold_float
        elif operator == 'lte':
            return metric_value <= threshold_float
        elif operator == 'eq':
            return abs(metric_value - threshold_float) < 0.01
        elif operator == 'ne':
            return abs(metric_value - threshold_float) >= 0.01
        
        return False
    
    def _calculate_new_value(self, entity, rule: AutomationRule, metrics: Dict) -> str:
        """
        Calculate new value based on rule action.
        
        TODO: Phase 3 - Implement value calculation
        """
        if rule.rule_type == 'keyword_bid':
            current_bid = float(entity.bid) if entity.bid else 0
            
            if rule.action_percentage:
                change = current_bid * (float(rule.action_percentage) / 100)
                new_bid = current_bid + change
            elif rule.action_value:
                new_bid = float(rule.action_value)
            else:
                new_bid = current_bid
            
            # Apply min/max constraints
            if rule.min_bid:
                new_bid = max(new_bid, float(rule.min_bid))
            if rule.max_bid:
                new_bid = min(new_bid, float(rule.max_bid))
            
            return str(Decimal(str(new_bid)).quantize(Decimal('0.01')))
        
        return ''
    
    def _check_safety(self, entity, rule: AutomationRule, new_value: str) -> tuple:
        """
        Perform safety checks before executing action.
        
        TODO: Phase 3 - Implement comprehensive safety checks
        """
        # Check daily limits
        today = timezone.now().date()
        today_executions = AutopilotExecution.objects.filter(
            account=self.account,
            rule__rule_type=rule.rule_type,
            executed_at__date=today,
            status='executed'
        ).count()
        
        if rule.rule_type == 'keyword_bid':
            if today_executions >= self.safety_limits.max_bid_changes_per_day:
                return False, f"Daily bid change limit reached ({self.safety_limits.max_bid_changes_per_day})"
        
        # Check bid change percentage
        if rule.rule_type == 'keyword_bid' and entity.bid:
            old_bid = float(entity.bid)
            new_bid = float(new_value)
            change_percent = abs((new_bid - old_bid) / old_bid * 100)
            
            if change_percent > float(rule.max_bid_change_percent):
                return False, f"Bid change exceeds max allowed ({rule.max_bid_change_percent}%)"
        
        return True, ''
    
    def _create_execution(
        self,
        rule: AutomationRule,
        entity=None,
        status='pending',
        condition_met=False,
        metric_value=None,
        old_value=None,
        new_value=None,
        reason='',
        safety_check_passed=True,
        safety_reason=''
    ) -> AutopilotExecution:
        """
        Create execution record.
        """
        execution = AutopilotExecution.objects.create(
            rule=rule,
            account=self.account,
            status=status,
            entity_type=type(entity).__name__.lower() if entity else '',
            entity_id=str(entity.id) if entity else '',
            condition_met=condition_met,
            metric_value=metric_value,
            old_value=old_value or (str(entity.bid) if entity and hasattr(entity, 'bid') else ''),
            new_value=new_value or '',
            reason=reason,
            safety_check_passed=safety_check_passed,
            safety_reason=safety_reason
        )
        
        return execution

