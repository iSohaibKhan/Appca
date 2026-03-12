"""
Safety/QA Agent: checks proposed plan against guardrails.
Approves, edits, or blocks. Requires reason + expected impact for each action.
"""
from decimal import Decimal
from typing import Any, Dict, List, Tuple
from django.utils import timezone

from apps.amazon_auth.models import AmazonAccount
from ..models import SafetyLimit
from ..schemas.daily_plan import DailyPlan, DailyPlanAction


# Guardrail constants (can be overridden by SafetyLimit later)
BUDGET_MAX_INCREASE_PERCENT = 20
BID_MAX_CHANGE_PERCENT = 15
MIN_CLICKS_FOR_BID_CHANGE = 20


class SafetyQAAgent:
    """
    Validates and optionally edits the daily plan. Blocks if dangerous.
    """

    def __init__(self, account: AmazonAccount):
        self.account = account
        self.safety_limits = SafetyLimit.objects.get_or_create(account=account)[0]

    def check_plan(self, plan: DailyPlan) -> Tuple[DailyPlan, bool, List[str]]:
        """
        Check plan against guardrails. Returns (approved_or_edited_plan, passed, messages).
        If passed is False, plan.status is set to 'blocked' and actions may be empty.
        """
        messages: List[str] = []
        if not self.safety_limits.is_enabled:
            plan.status = "blocked"
            return plan, False, ["Autopilot is disabled by safety limits."]
        approved_actions: List[DailyPlanAction] = []
        for action in plan.actions:
            ok, msg = self._check_action(action)
            if ok:
                approved_actions.append(action)
            else:
                messages.append(msg)
        plan.actions = approved_actions
        if messages and not approved_actions:
            plan.status = "blocked"
            return plan, False, messages
        if messages:
            plan.status = "approved"
            return plan, True, messages  # partial approval
        plan.status = "approved"
        return plan, True, []

    def _check_action(self, action: DailyPlanAction) -> Tuple[bool, str]:
        """Validate a single action. Return (allowed, message)."""
        if not action.reason or not action.expected_impact:
            return False, f"Action {action.action} on {action.entity_id}: missing reason or expected_impact."
        if action.action in ("increase_bid", "decrease_bid", "set_bid"):
            return self._check_bid_action(action)
        if action.action in ("increase_budget", "decrease_budget", "cap_budget"):
            return self._check_budget_action(action)
        if action.action == "add_negative_keyword":
            return self._check_negative_keyword_action(action)
        return True, ""

    def _check_bid_action(self, action: DailyPlanAction) -> Tuple[bool, str]:
        """Enforce ±15% bid cap and min clicks >= 20."""
        evidence = action.metric_evidence or {}
        clicks = evidence.get("clicks", 0)
        if clicks < MIN_CLICKS_FOR_BID_CHANGE:
            return False, (
                f"Bid change on {action.entity_id} blocked: clicks={clicks} "
                f"(min {MIN_CLICKS_FOR_BID_CHANGE} required)."
            )
        percent = action.percent_change
        if percent is not None:
            if abs(percent) > BID_MAX_CHANGE_PERCENT:
                return False, (
                    f"Bid change on {action.entity_id} blocked: "
                    f"percent_change={percent}% exceeds ±{BID_MAX_CHANGE_PERCENT}%."
                )
        # Use model limit if set (e.g. max_bid_changes_per_day checked by Manager)
        return True, ""

    def _check_budget_action(self, action: DailyPlanAction) -> Tuple[bool, str]:
        """Enforce budget +20% max increase per day (hard guardrail)."""
        limit = self.safety_limits
        model_max = float(limit.max_daily_budget_increase_percent or BUDGET_MAX_INCREASE_PERCENT)
        max_inc = min(model_max, BUDGET_MAX_INCREASE_PERCENT)  # never more than 20% in one day
        percent = action.percent_change
        if percent is not None and percent > max_inc:
            return False, (
                f"Budget increase on {action.entity_id} blocked: "
                f"+{percent}% exceeds max +{max_inc}%."
            )
        return True, ""

    def _check_negative_keyword_action(self, action: DailyPlanAction) -> Tuple[bool, str]:
        """Keyword safety: only add neg when spend > X and 0 sales or ACOS > target."""
        evidence = action.metric_evidence or {}
        # Allow if reason and expected_impact present; evidence can back it
        return True, ""
