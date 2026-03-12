"""
Optimizer Agent: proposes actions (bid up/down, budget caps, neg keywords) from metrics.
Outputs a daily plan (JSON-serializable) with reason and expected impact.
"""
from typing import Any, Dict, List, Optional
from django.utils import timezone

from apps.amazon_auth.models import AmazonAccount
from ..schemas.daily_plan import DailyPlan, DailyPlanAction


class OptimizerAgent:
    """
    Consumes metrics from Analyst and produces a list of proposed actions.
    Uses policy rules (e.g. ACOS target, min clicks for bid change).
    """

    def __init__(self, account: AmazonAccount, acos_target: float = 25.0, min_clicks_for_bid_change: int = 20):
        self.account = account
        self.acos_target = acos_target
        self.min_clicks_for_bid_change = min_clicks_for_bid_change

    def propose_plan(self, metrics: Dict[str, Any]) -> DailyPlan:
        """
        Build daily plan from metrics. Mock/simple rules for MVP.
        """
        actions: List[DailyPlanAction] = []
        for kw in metrics.get("keywords", []):
            action = self._evaluate_keyword(kw)
            if action:
                actions.append(action)
        for camp in metrics.get("campaigns", []):
            action = self._evaluate_campaign_budget(camp)
            if action:
                actions.append(action)
        return DailyPlan(
            actions=actions,
            generated_at=timezone.now().isoformat(),
            account_id=self.account.id,
            status="draft",
        )

    def _evaluate_keyword(self, kw: Dict[str, Any]) -> Optional[DailyPlanAction]:
        """Propose bid change if ACOS/clicks rules met."""
        clicks = kw.get("clicks", 0)
        cost = kw.get("cost", 0)
        sales = kw.get("sales", 0)
        bid = kw.get("bid", 0)
        if not bid or bid <= 0:
            return None
        acos = (cost / sales * 100) if sales else 999
        # No bid change if insufficient data
        if clicks < self.min_clicks_for_bid_change:
            return None
        # High ACOS, 0 sales or above target -> decrease bid
        if sales == 0 and cost > 0:
            new_bid = round(bid * 0.9, 2)
            return DailyPlanAction(
                action="decrease_bid",
                entity_type="keyword",
                entity_id=kw.get("keyword_id", ""),
                ad_group_id=kw.get("ad_group_id"),
                campaign_id=kw.get("campaign_id"),
                value=new_bid,
                percent_change=-10,
                reason="0 sales with spend; reduce bid to limit waste",
                expected_impact="Lower cost, may recover conversions later",
                metric_evidence={"clicks": clicks, "cost": cost, "sales": sales, "acos": acos},
            )
        if acos > self.acos_target and sales > 0:
            new_bid = round(bid * 0.9, 2)
            return DailyPlanAction(
                action="decrease_bid",
                entity_type="keyword",
                entity_id=kw.get("keyword_id", ""),
                ad_group_id=kw.get("ad_group_id"),
                campaign_id=kw.get("campaign_id"),
                value=new_bid,
                percent_change=-10,
                reason=f"ACOS {acos}% above target {self.acos_target}%",
                expected_impact="Lower ACOS",
                metric_evidence={"clicks": clicks, "acos": acos},
            )
        # Low ACOS, good conversions -> increase bid slightly
        if acos < self.acos_target * 0.7 and sales > 0 and clicks >= self.min_clicks_for_bid_change:
            new_bid = round(bid * 1.05, 2)
            return DailyPlanAction(
                action="increase_bid",
                entity_type="keyword",
                entity_id=kw.get("keyword_id", ""),
                ad_group_id=kw.get("ad_group_id"),
                campaign_id=kw.get("campaign_id"),
                value=new_bid,
                percent_change=5,
                reason=f"ACOS {acos}% below target; scale up",
                expected_impact="More traffic, maintain margin",
                metric_evidence={"clicks": clicks, "acos": acos},
            )
        return None

    def _evaluate_campaign_budget(self, camp: Dict[str, Any]) -> Optional[DailyPlanAction]:
        """Optionally propose budget cap change. Conservative for MVP."""
        return None
