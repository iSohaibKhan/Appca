"""
Daily plan schema for Autopilot.
JSON-serializable structure for proposed and approved actions.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class ActionType(str, Enum):
    INCREASE_BID = "increase_bid"
    DECREASE_BID = "decrease_bid"
    SET_BID = "set_bid"
    CAP_BUDGET = "cap_budget"
    INCREASE_BUDGET = "increase_budget"
    DECREASE_BUDGET = "decrease_budget"
    ADD_NEGATIVE_KEYWORD = "add_negative_keyword"
    PAUSE_KEYWORD = "pause_keyword"
    ENABLE_KEYWORD = "enable_keyword"
    PAUSE_CAMPAIGN = "pause_campaign"
    ENABLE_CAMPAIGN = "enable_campaign"


class EntityType(str, Enum):
    KEYWORD = "keyword"
    AD_GROUP = "ad_group"
    CAMPAIGN = "campaign"


@dataclass
class DailyPlanAction:
    """A single proposed or approved action in the daily plan."""
    action: str  # ActionType value
    entity_type: str  # EntityType value
    entity_id: str
    # Optional identifiers for display/API
    campaign_id: Optional[str] = None
    ad_group_id: Optional[str] = None
    # Action parameters
    value: Optional[float] = None  # bid amount, budget amount, etc.
    percent_change: Optional[float] = None  # e.g. 10 for +10%
    # For negative keyword
    keyword_text: Optional[str] = None
    match_type: Optional[str] = None  # exact, phrase
    # Audit
    reason: str = ""
    expected_impact: str = ""
    metric_evidence: Optional[Dict[str, Any]] = None  # e.g. {"clicks": 50, "acos": 25}

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "reason": self.reason,
            "expected_impact": self.expected_impact,
        }
        if self.campaign_id is not None:
            d["campaign_id"] = self.campaign_id
        if self.ad_group_id is not None:
            d["ad_group_id"] = self.ad_group_id
        if self.value is not None:
            d["value"] = self.value
        if self.percent_change is not None:
            d["percent_change"] = self.percent_change
        if self.keyword_text is not None:
            d["keyword_text"] = self.keyword_text
        if self.match_type is not None:
            d["match_type"] = self.match_type
        if self.metric_evidence is not None:
            d["metric_evidence"] = self.metric_evidence
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DailyPlanAction":
        return cls(
            action=d["action"],
            entity_type=d["entity_type"],
            entity_id=d["entity_id"],
            campaign_id=d.get("campaign_id"),
            ad_group_id=d.get("ad_group_id"),
            value=d.get("value"),
            percent_change=d.get("percent_change"),
            keyword_text=d.get("keyword_text"),
            match_type=d.get("match_type"),
            reason=d.get("reason", ""),
            expected_impact=d.get("expected_impact", ""),
            metric_evidence=d.get("metric_evidence"),
        )


@dataclass
class DailyPlan:
    """Daily plan: list of actions with optional metadata."""
    actions: List[DailyPlanAction] = field(default_factory=list)
    generated_at: Optional[str] = None  # ISO timestamp
    account_id: Optional[int] = None
    status: str = "draft"  # draft | approved | blocked | applied

    def to_dict(self) -> Dict[str, Any]:
        return {
            "actions": [a.to_dict() for a in self.actions],
            "generated_at": self.generated_at,
            "account_id": self.account_id,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DailyPlan":
        return cls(
            actions=[DailyPlanAction.from_dict(a) for a in d.get("actions", [])],
            generated_at=d.get("generated_at"),
            account_id=d.get("account_id"),
            status=d.get("status", "draft"),
        )
