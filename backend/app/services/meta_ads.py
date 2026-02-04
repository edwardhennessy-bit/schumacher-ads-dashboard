"""
Meta Ads data service for Schumacher Homes dashboard.

This service provides real Meta Ads data fetched from the MCP Gateway.
Data is stored in JSON files and refreshed periodically.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from app.models.schemas import (
    MetricsOverview,
    DailyMetric,
    Campaign,
)

DATA_DIR = Path(__file__).parent.parent.parent / "data"


class MetaAdsService:
    """Service for accessing Meta Ads data from exported JSON files."""

    def __init__(self):
        self.data_dir = DATA_DIR
        self.data_dir.mkdir(exist_ok=True)

    def _load_json(self, filename: str) -> Optional[dict]:
        """Load JSON data from file."""
        filepath = self.data_dir / filename
        if filepath.exists():
            with open(filepath, "r") as f:
                return json.load(f)
        return None

    def _get_action_value(self, actions: list, action_type: str) -> int:
        """Extract value for a specific action type from actions list."""
        if not actions:
            return 0
        for action in actions:
            if action.get("action_type") == action_type:
                return int(action.get("value", 0))
        return 0

    def get_metrics_overview(self) -> MetricsOverview:
        """Get metrics overview from real Meta Ads data."""
        data = self._load_json("metrics_overview.json")
        if data:
            return MetricsOverview(**data)

        # Fallback to current period data if available
        current = self._load_json("account_insights_current.json")
        previous = self._load_json("account_insights_previous.json")

        if current:
            return self._build_metrics_overview(current, previous)

        # Return empty metrics if no data available
        return self._empty_metrics_overview()

    def _build_metrics_overview(
        self, current: dict, previous: Optional[dict] = None
    ) -> MetricsOverview:
        """Build MetricsOverview from raw API data."""
        # Extract current period values
        spend = float(current.get("spend", 0))
        impressions = int(current.get("impressions", 0))
        clicks = int(current.get("clicks", 0))
        reach = int(current.get("reach", 0))
        ctr = float(current.get("ctr", 0))
        cpc = float(current.get("cpc", 0))
        cpm = float(current.get("cpm", 0))

        actions = current.get("actions", [])
        leads = self._get_action_value(actions, "lead")
        conversions = self._get_action_value(
            actions, "offsite_conversion.fb_pixel_lead"
        )
        landing_page_views = self._get_action_value(actions, "landing_page_view")

        # Calculate derived metrics
        cost_per_lead = round(spend / leads, 2) if leads > 0 else 0
        lead_rate = round((leads / clicks) * 100, 2) if clicks > 0 else 0

        # Calculate changes from previous period
        def calc_change(curr: float, prev: float) -> float:
            if prev == 0:
                return 0
            return round(((curr - prev) / prev) * 100, 1)

        if previous:
            prev_spend = float(previous.get("spend", 0))
            prev_impressions = int(previous.get("impressions", 0))
            prev_clicks = int(previous.get("clicks", 0))
            prev_ctr = float(previous.get("ctr", 0))
            prev_cpc = float(previous.get("cpc", 0))
            prev_cpm = float(previous.get("cpm", 0))
            prev_actions = previous.get("actions", [])
            prev_leads = self._get_action_value(prev_actions, "lead")
            prev_conversions = self._get_action_value(
                prev_actions, "offsite_conversion.fb_pixel_lead"
            )
            prev_cost_per_lead = (
                round(prev_spend / prev_leads, 2) if prev_leads > 0 else 0
            )
            prev_lead_rate = (
                round((prev_leads / prev_clicks) * 100, 2) if prev_clicks > 0 else 0
            )

            spend_change = calc_change(spend, prev_spend)
            impressions_change = calc_change(impressions, prev_impressions)
            clicks_change = calc_change(clicks, prev_clicks)
            ctr_change = calc_change(ctr, prev_ctr)
            cpc_change = calc_change(cpc, prev_cpc)
            cpm_change = calc_change(cpm, prev_cpm)
            leads_change = calc_change(leads, prev_leads)
            conversions_change = calc_change(conversions, prev_conversions)
            cost_per_lead_change = calc_change(cost_per_lead, prev_cost_per_lead)
            lead_rate_change = calc_change(lead_rate, prev_lead_rate)
        else:
            spend_change = 0
            impressions_change = 0
            clicks_change = 0
            ctr_change = 0
            cpc_change = 0
            cpm_change = 0
            leads_change = 0
            conversions_change = 0
            cost_per_lead_change = 0
            lead_rate_change = 0

        # Get ad inventory counts (actual individual ads, not campaigns)
        ad_inventory = self._load_json("ad_inventory.json")
        if ad_inventory:
            active_ads = ad_inventory.get("active_ads", 0)
            total_ads = ad_inventory.get("total_ads", 0)
            active_ads_threshold = ad_inventory.get("threshold", 250)
        else:
            # Fallback to campaign counts if no ad inventory data
            campaigns_data = self._load_json("campaigns.json")
            if campaigns_data:
                active_ads = sum(
                    1 for c in campaigns_data if c.get("status") == "ACTIVE"
                )
                total_ads = len(campaigns_data)
            else:
                active_ads = 204  # From ad-level query with effective_status
                total_ads = 2500
            active_ads_threshold = 250

        # Calculate segmented CPL (Remarketing vs Prospecting)
        campaigns_data = self._load_json("campaigns.json")
        remarketing_spend = 0
        remarketing_leads = 0
        prospecting_spend = 0
        prospecting_leads = 0

        if campaigns_data:
            for camp in campaigns_data:
                camp_name = camp.get("name", "").lower()
                camp_spend = camp.get("spend", 0)
                camp_leads = camp.get("leads", 0)

                if "remarketing" in camp_name:
                    remarketing_spend += camp_spend
                    remarketing_leads += camp_leads
                elif "tof" not in camp_name:
                    # Exclude TOF (traffic/awareness) campaigns from Prospecting CPL
                    # Only include MOF/BOF campaigns optimized for leads
                    prospecting_spend += camp_spend
                    prospecting_leads += camp_leads

        remarketing_cpl = round(remarketing_spend / remarketing_leads, 2) if remarketing_leads > 0 else 0
        prospecting_cpl = round(prospecting_spend / prospecting_leads, 2) if prospecting_leads > 0 else 0

        return MetricsOverview(
            spend=spend,
            spend_change=spend_change,
            impressions=impressions,
            impressions_change=impressions_change,
            clicks=clicks,
            clicks_change=clicks_change,
            ctr=round(ctr, 2),
            ctr_change=ctr_change,
            cpc=round(cpc, 2),
            cpc_change=cpc_change,
            cpm=round(cpm, 2),
            cpm_change=cpm_change,
            conversions=conversions if conversions > 0 else leads,
            conversions_change=conversions_change,
            leads=leads,
            leads_change=leads_change,
            cost_per_lead=cost_per_lead,
            cost_per_lead_change=cost_per_lead_change,
            lead_rate=lead_rate,
            lead_rate_change=lead_rate_change,
            remarketing_leads=remarketing_leads,
            remarketing_spend=round(remarketing_spend, 2),
            remarketing_cpl=remarketing_cpl,
            prospecting_leads=prospecting_leads,
            prospecting_spend=round(prospecting_spend, 2),
            prospecting_cpl=prospecting_cpl,
            active_ads=active_ads,
            total_ads=total_ads,
            active_ads_threshold=active_ads_threshold,
        )

    def _empty_metrics_overview(self) -> MetricsOverview:
        """Return empty metrics overview."""
        return MetricsOverview(
            spend=0,
            spend_change=0,
            impressions=0,
            impressions_change=0,
            clicks=0,
            clicks_change=0,
            ctr=0,
            ctr_change=0,
            cpc=0,
            cpc_change=0,
            cpm=0,
            cpm_change=0,
            conversions=0,
            conversions_change=0,
            leads=0,
            leads_change=0,
            cost_per_lead=0,
            cost_per_lead_change=0,
            lead_rate=0,
            lead_rate_change=0,
            active_ads=0,
            total_ads=0,
        )

    def get_trend_data(self, days: int = 30) -> List[DailyMetric]:
        """Get daily trend data."""
        data = self._load_json("daily_trends.json")
        if data:
            # Return only the requested number of days
            trends = [DailyMetric(**d) for d in data]
            return trends[-days:] if len(trends) > days else trends

        # Return empty list if no data
        return []

    def get_campaigns(self) -> List[Campaign]:
        """Get all campaigns with performance data."""
        data = self._load_json("campaigns.json")
        if data:
            return [Campaign(**c) for c in data]
        return []

    def get_campaign(self, campaign_id: str) -> Optional[Campaign]:
        """Get a single campaign by ID."""
        campaigns = self.get_campaigns()
        for campaign in campaigns:
            if campaign.id == campaign_id:
                return campaign
        return None
