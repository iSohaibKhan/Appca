"""
Manager (Orchestrator) Agent: applies approved plan via Ads API and produces report.
"""
from typing import Any, Dict, List
from django.utils import timezone

from apps.amazon_auth.models import AmazonAccount
from apps.amazon_ads.services.api_service import AmazonAdsAPIService
from apps.audit_logs.models import AuditLog
from ..schemas.daily_plan import DailyPlan, DailyPlanAction


class ManagerAgent:
    """
    Applies only QA-approved actions. Logs each change. Produces final report.
    """

    def __init__(self, account: AmazonAccount):
        self.account = account

    def apply_plan(self, plan: DailyPlan) -> Dict[str, Any]:
        """
        Apply approved plan. Returns report with applied, failed, skipped.
        Only runs when plan.status == 'approved'.
        """
        report = {
            "account_id": self.account.id,
            "plan_status": plan.status,
            "applied": [],
            "failed": [],
            "skipped": [],
            "generated_at": timezone.now().isoformat(),
        }
        if plan.status != "approved":
            report["skipped"] = [{"reason": f"Plan status is {plan.status}, not approved"}]
            return report
        api = AmazonAdsAPIService(self.account)
        for action in plan.actions:
            result = self._apply_action(api, action)
            if result["status"] == "applied":
                report["applied"].append(result)
            elif result["status"] == "failed":
                report["failed"].append(result)
            else:
                report["skipped"].append(result)
        return report

    def _apply_action(self, api: AmazonAdsAPIService, action: DailyPlanAction) -> Dict[str, Any]:
        """Apply one action and log. Returns {status, action_type, entity_id, detail}."""
        try:
            if action.action in ("increase_bid", "decrease_bid", "set_bid") and action.value is not None:
                api.update_keyword_bid(action.entity_id, float(action.value))
                AuditLog.objects.create(
                    account=self.account,
                    action="keyword_bid_update",
                    entity_type="keyword",
                    entity_id=action.entity_id,
                    new_value=str(action.value),
                    reason=action.reason,
                )
                return {"status": "applied", "action_type": action.action, "entity_id": action.entity_id, "detail": str(action.value)}
            if action.action in ("cap_budget", "increase_budget", "decrease_budget") and action.value is not None and action.entity_type == "campaign":
                api.update_campaign_budget(action.entity_id, float(action.value))
                AuditLog.objects.create(
                    account=self.account,
                    action="campaign_budget_update",
                    entity_type="campaign",
                    entity_id=action.entity_id,
                    new_value=str(action.value),
                    reason=action.reason,
                )
                return {"status": "applied", "action_type": action.action, "entity_id": action.entity_id, "detail": str(action.value)}
        except Exception as e:
            return {"status": "failed", "action_type": action.action, "entity_id": action.entity_id, "detail": str(e)}
        return {"status": "skipped", "action_type": action.action, "entity_id": action.entity_id, "detail": "Unsupported action or missing value"}
