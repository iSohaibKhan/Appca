"""
Data/Analyst Agent: pulls metrics, computes KPIs, flags anomalies.
Uses mock data when real report ingestion is not available.
"""
from datetime import timedelta
from typing import Any, Dict, List
from django.utils import timezone

from apps.amazon_auth.models import AmazonAccount
from apps.amazon_ads.models import Campaign, Keyword, KeywordPerformance, CampaignPerformance


class AnalystAgent:
    """
    Produces metrics and insights for an account over a lookback period.
    """

    def __init__(self, account: AmazonAccount):
        self.account = account

    def get_metrics(
        self,
        lookback_days: int = 7,
        use_mock_if_empty: bool = True,
    ) -> Dict[str, Any]:
        """
        Pull metrics for the account (campaigns, keywords, KPIs).
        Returns dict with keys: campaigns, keywords, summary, anomalies.
        """
        date_from = timezone.now().date() - timedelta(days=lookback_days)
        metrics = {
            "account_id": self.account.id,
            "lookback_days": lookback_days,
            "date_from": str(date_from),
            "campaigns": [],
            "keywords": [],
            "summary": {"spend": 0, "sales": 0, "clicks": 0, "orders": 0, "acos": 0, "roas": 0},
            "anomalies": [],
        }
        try:
            campaigns = Campaign.objects.filter(account=self.account)
            for camp in campaigns:
                camp_metrics = self._campaign_metrics(camp, date_from)
                metrics["campaigns"].append(camp_metrics)
                self._aggregate_summary(metrics["summary"], camp_metrics)
            keywords = Keyword.objects.filter(ad_group__campaign__account=self.account)
            for kw in keywords:
                kw_metrics = self._keyword_metrics(kw, date_from)
                metrics["keywords"].append(kw_metrics)
            self._flag_anomalies(metrics)
        except Exception:
            if use_mock_if_empty:
                metrics = self._mock_metrics(lookback_days, date_from)
        return metrics

    def _campaign_metrics(self, campaign, date_from) -> Dict[str, Any]:
        """Aggregate campaign performance over date range."""
        perfs = CampaignPerformance.objects.filter(
            campaign=campaign,
            date__gte=date_from,
        )
        spend = sum(float(p.cost) for p in perfs)
        sales = sum(float(p.sales) for p in perfs)
        clicks = sum(p.clicks for p in perfs)
        orders = sum(p.orders for p in perfs)
        return {
            "campaign_id": campaign.campaign_id,
            "name": campaign.name,
            "spend": round(spend, 2),
            "sales": round(sales, 2),
            "clicks": clicks,
            "orders": orders,
            "daily_budget": float(campaign.daily_budget or 0),
        }

    def _keyword_metrics(self, keyword, date_from) -> Dict[str, Any]:
        """Aggregate keyword performance."""
        performances = KeywordPerformance.objects.filter(
            keyword=keyword,
            date__gte=date_from,
        )
        if not performances.exists():
            ag = getattr(keyword, "ad_group", None)
            campaign_id = None
            if ag:
                camp = getattr(ag, "campaign", None)
                campaign_id = getattr(camp, "campaign_id", str(camp.id)) if camp else None
            return {
                "keyword_id": getattr(keyword, "keyword_id", str(keyword.id)),
                "ad_group_id": getattr(ag, "ad_group_id", str(ag.id)) if ag else None,
                "campaign_id": campaign_id,
                "clicks": 0,
                "cost": 0,
                "sales": 0,
                "orders": 0,
                "acos": 0,
                "roas": 0,
                "bid": float(keyword.bid or 0),
            }
        total_cost = sum(p.cost for p in performances)
        total_sales = sum(p.sales for p in performances)
        total_clicks = sum(p.clicks for p in performances)
        total_orders = sum(p.orders for p in performances)
        acos = (total_cost / total_sales * 100) if total_sales else 0
        roas = total_sales / total_cost if total_cost else 0
        ag = getattr(keyword, "ad_group", None)
        campaign_id = None
        if ag:
            camp = getattr(ag, "campaign", None)
            campaign_id = getattr(camp, "campaign_id", str(camp.id)) if camp else None
        return {
            "keyword_id": getattr(keyword, "keyword_id", str(keyword.id)),
            "ad_group_id": getattr(ag, "ad_group_id", str(ag.id)) if ag else None,
            "campaign_id": campaign_id,
            "clicks": total_clicks,
            "cost": float(total_cost),
            "sales": float(total_sales),
            "orders": total_orders,
            "acos": round(acos, 2),
            "roas": round(roas, 2),
            "bid": float(keyword.bid or 0),
        }

    def _aggregate_summary(self, summary: Dict, camp: Dict) -> None:
        summary["spend"] += camp.get("spend", 0)
        summary["sales"] += camp.get("sales", 0)
        summary["clicks"] += camp.get("clicks", 0)
        summary["orders"] += camp.get("orders", 0)
        if summary["sales"]:
            summary["acos"] = round(summary["spend"] / summary["sales"] * 100, 2)
        if summary["spend"]:
            summary["roas"] = round(summary["sales"] / summary["spend"], 2)

    def _flag_anomalies(self, metrics: Dict) -> None:
        """Append anomaly messages (e.g. spend spike, CVR drop)."""
        s = metrics["summary"]
        if s.get("spend", 0) > 500 and s.get("orders", 0) == 0:
            metrics["anomalies"].append("High spend with zero orders in period")
        for kw in metrics.get("keywords", []):
            if kw.get("clicks", 0) >= 20 and kw.get("orders", 0) == 0 and kw.get("cost", 0) > 5:
                metrics["anomalies"].append(
                    f"Keyword {kw.get('keyword_id')}: clicks={kw.get('clicks')}, 0 orders, cost={kw.get('cost')}"
                )

    def _mock_metrics(self, lookback_days: int, date_from) -> Dict[str, Any]:
        """Return mock metrics for testing without API/reports."""
        return {
            "account_id": self.account.id,
            "lookback_days": lookback_days,
            "date_from": str(date_from),
            "campaigns": [
                {
                    "campaign_id": "mock_camp_1",
                    "name": "Mock Campaign",
                    "spend": 100,
                    "sales": 400,
                    "clicks": 50,
                    "orders": 8,
                    "daily_budget": 20.0,
                }
            ],
            "keywords": [
                {
                    "keyword_id": "mock_kw_1",
                    "ad_group_id": "mock_ag_1",
                    "campaign_id": "mock_camp_1",
                    "clicks": 25,
                    "cost": 50,
                    "sales": 200,
                    "orders": 4,
                    "acos": 25,
                    "roas": 4,
                    "bid": 1.5,
                }
            ],
            "summary": {"spend": 100, "sales": 400, "clicks": 50, "orders": 8, "acos": 25, "roas": 4},
            "anomalies": [],
        }
