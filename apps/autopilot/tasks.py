"""
Celery tasks for Autopilot automation.
"""
from celery import shared_task
from django.utils import timezone
from .models import AutopilotGoal
from .services.decision_engine import DecisionEngine
from .services.daily_loop import run_daily_loop
from apps.amazon_ads.tasks import update_keyword_bid


@shared_task
def run_daily_agent_loop():
    """
    Run the 4-agent daily loop (Analyst -> Optimizer -> Safety -> Manager) for all connected accounts.
    Non-API-reliant: uses mock metrics when reports are empty; applies only QA-approved actions.
    """
    from apps.amazon_auth.models import AmazonAccount
    active = AmazonAccount.objects.filter(is_active=True, is_connected=True)
    for account in active:
        try:
            run_daily_loop(account, lookback_days=7, apply_if_approved=True)
        except Exception as e:
            # Log and continue with other accounts
            import logging
            logging.getLogger(__name__).exception("Daily agent loop failed for account %s: %s", account.id, e)


@shared_task
def run_autopilot_daily():
    """
    Daily autopilot execution task.
    Evaluates all active rules and executes actions.
    
    TODO: Phase 3 - Set up Celery Beat schedule (daily at 2 AM)
    TODO: Phase 3 - Implement action execution
    """
    from apps.amazon_auth.models import AmazonAccount
    
    active_accounts = AmazonAccount.objects.filter(
        is_active=True,
        is_connected=True
    )
    
    for account in active_accounts:
        try:
            engine = DecisionEngine(account)
            executions = engine.evaluate_rules()
            
            # Execute actions
            for execution in executions:
                if execution.status == 'pending' and execution.safety_check_passed:
                    _execute_action(execution)
                    
        except Exception as e:
            print(f"Error running autopilot for account {account.id}: {e}")


def _execute_action(execution):
    """
    Execute an autopilot action.
    
    TODO: Phase 3 - Implement action execution
    """
    rule = execution.rule
    
    if rule.rule_type == 'keyword_bid':
        # Update keyword bid
        update_keyword_bid.delay(execution.entity_id, execution.new_value)
        execution.status = 'executed'
        execution.save()
    elif rule.rule_type == 'keyword_pause':
        # TODO: Phase 3 - Pause keyword
        pass
    elif rule.rule_type == 'campaign_budget':
        # TODO: Phase 3 - Update campaign budget
        pass
    # ... other action types

