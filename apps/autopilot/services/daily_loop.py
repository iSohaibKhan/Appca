"""
Daily agent loop: Analyst -> Optimizer -> Safety/QA -> Manager.
Runs once per day per account. Stops if QA blocks.
"""
from typing import Any, Dict, Optional

from apps.amazon_auth.models import AmazonAccount
from .analyst_agent import AnalystAgent
from .optimizer_agent import OptimizerAgent
from .safety_qa_agent import SafetyQAAgent
from .manager_agent import ManagerAgent
from ..schemas.daily_plan import DailyPlan


def run_daily_loop(
    account: AmazonAccount,
    lookback_days: int = 7,
    apply_if_approved: bool = True,
) -> Dict[str, Any]:
    """
    Run the full pipeline: pull metrics -> propose plan -> QA check -> apply (if approved).
    Returns summary with plan, report, and whether applied.
    """
    analyst = AnalystAgent(account)
    optimizer = OptimizerAgent(account)
    safety = SafetyQAAgent(account)
    manager = ManagerAgent(account)

    metrics = analyst.get_metrics(lookback_days=lookback_days, use_mock_if_empty=True)
    plan = optimizer.propose_plan(metrics)
    plan, qa_passed, qa_messages = safety.check_plan(plan)

    result = {
        "account_id": account.id,
        "metrics_summary": metrics.get("summary", {}),
        "plan": plan.to_dict(),
        "qa_passed": qa_passed,
        "qa_messages": qa_messages,
        "applied": False,
        "report": None,
    }
    if not qa_passed:
        result["report"] = {"blocked": True, "messages": qa_messages}
        return result
    if apply_if_approved and plan.status == "approved" and plan.actions:
        report = manager.apply_plan(plan)
        result["report"] = report
        result["applied"] = bool(report.get("applied"))
    else:
        result["report"] = {"applied": 0, "skipped": "No actions or not applying"}
    return result
