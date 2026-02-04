"""Mock data service for development before Meta Ads account is connected."""

import random
from datetime import datetime, timedelta
from typing import List

from app.models.schemas import (
    MetricsOverview,
    DailyMetric,
    Campaign,
    AuditAlert,
)


class MockDataService:
    """Provides mock data for dashboard development."""

    def get_metrics_overview(self) -> MetricsOverview:
        """Get mock metrics overview."""
        # Calculate lead metrics
        leads = 312
        clicks = 42847
        spend = 45872.34
        cost_per_lead = spend / leads if leads else 0
        lead_rate = (leads / clicks) * 100 if clicks else 0

        return MetricsOverview(
            spend=spend,
            spend_change=12.5,
            impressions=2847593,
            impressions_change=8.3,
            clicks=clicks,
            clicks_change=15.2,
            ctr=1.50,
            ctr_change=6.4,
            cpc=1.07,
            cpc_change=-2.3,
            cpm=16.11,
            cpm_change=3.9,
            conversions=847,
            conversions_change=22.1,
            # Lead metrics
            leads=leads,
            leads_change=18.7,
            cost_per_lead=round(cost_per_lead, 2),
            cost_per_lead_change=-5.2,
            lead_rate=round(lead_rate, 2),
            lead_rate_change=3.1,
            active_ads=47,
            total_ads=62,
        )

    def get_trend_data(self, days: int = 30) -> List[DailyMetric]:
        """Get mock daily trend data."""
        data = []
        for i in range(days):
            date = datetime.now() - timedelta(days=days - 1 - i)
            base_spend = 1500 + random.random() * 500
            day_of_week = date.weekday()
            weekend_multiplier = 0.7 if day_of_week >= 5 else 1

            spend = round(base_spend * weekend_multiplier, 2)
            impressions = int((85000 + random.random() * 30000) * weekend_multiplier)
            clicks = int((1200 + random.random() * 600) * weekend_multiplier)
            conversions = int((20 + random.random() * 20) * weekend_multiplier)
            # Leads are typically a subset of conversions (form submissions, calls, etc.)
            leads = int((8 + random.random() * 8) * weekend_multiplier)

            data.append(
                DailyMetric(
                    date=date.strftime("%Y-%m-%d"),
                    spend=spend,
                    impressions=impressions,
                    clicks=clicks,
                    conversions=conversions,
                    leads=leads,
                    ctr=round((clicks / impressions) * 100, 2) if impressions else 0,
                    cpc=round(spend / clicks, 2) if clicks else 0,
                    cpm=round((spend / impressions) * 1000, 2) if impressions else 0,
                    cost_per_lead=round(spend / leads, 2) if leads else 0,
                )
            )
        return data

    def get_campaigns(self) -> List[Campaign]:
        """Get mock campaigns."""
        return [
            Campaign(
                id="camp_001",
                name="Schumacher - Brand Awareness Q1",
                status="ACTIVE",
                objective="BRAND_AWARENESS",
                spend=12450.00,
                impressions=892340,
                clicks=12847,
                ctr=1.44,
                cpc=0.97,
                conversions=234,
                cost_per_conversion=53.21,
                leads=45,
                cost_per_lead=276.67,
                lead_rate=0.35,
            ),
            Campaign(
                id="camp_002",
                name="Custom Home Leads - Ohio",
                status="ACTIVE",
                objective="LEAD_GENERATION",
                spend=8932.50,
                impressions=456789,
                clicks=8234,
                ctr=1.80,
                cpc=1.08,
                conversions=189,
                cost_per_conversion=47.26,
                leads=87,
                cost_per_lead=102.67,
                lead_rate=1.06,
            ),
            Campaign(
                id="camp_003",
                name="Floor Plans Showcase",
                status="ACTIVE",
                objective="TRAFFIC",
                spend=6789.25,
                impressions=523456,
                clicks=7892,
                ctr=1.51,
                cpc=0.86,
                conversions=156,
                cost_per_conversion=43.52,
                leads=52,
                cost_per_lead=130.56,
                lead_rate=0.66,
            ),
            Campaign(
                id="camp_004",
                name="Model Home Open Houses",
                status="ACTIVE",
                objective="ENGAGEMENT",
                spend=5234.80,
                impressions=345678,
                clicks=5432,
                ctr=1.57,
                cpc=0.96,
                conversions=98,
                cost_per_conversion=53.42,
                leads=34,
                cost_per_lead=153.96,
                lead_rate=0.63,
            ),
            Campaign(
                id="camp_005",
                name="Retargeting - Site Visitors",
                status="ACTIVE",
                objective="CONVERSIONS",
                spend=4567.90,
                impressions=234567,
                clicks=4123,
                ctr=1.76,
                cpc=1.11,
                conversions=112,
                cost_per_conversion=40.78,
                leads=48,
                cost_per_lead=95.16,
                lead_rate=1.16,
            ),
            Campaign(
                id="camp_006",
                name="Spring Sale 2024",
                status="PAUSED",
                objective="CONVERSIONS",
                spend=3456.78,
                impressions=187654,
                clicks=2987,
                ctr=1.59,
                cpc=1.16,
                conversions=67,
                cost_per_conversion=51.59,
                leads=23,
                cost_per_lead=150.30,
                lead_rate=0.77,
            ),
            Campaign(
                id="camp_007",
                name="Video Tours Campaign",
                status="ACTIVE",
                objective="VIDEO_VIEWS",
                spend=2890.45,
                impressions=156789,
                clicks=2134,
                ctr=1.36,
                cpc=1.35,
                conversions=45,
                cost_per_conversion=64.23,
                leads=15,
                cost_per_lead=192.70,
                lead_rate=0.70,
            ),
            Campaign(
                id="camp_008",
                name="Builder Testimonials",
                status="PAUSED",
                objective="ENGAGEMENT",
                spend=1550.66,
                impressions=98765,
                clicks=1198,
                ctr=1.21,
                cpc=1.29,
                conversions=23,
                cost_per_conversion=67.42,
                leads=8,
                cost_per_lead=193.83,
                lead_rate=0.67,
            ),
        ]

    def get_audit_alerts(self) -> List[AuditAlert]:
        """Get mock audit alerts."""
        now = datetime.now()
        return [
            AuditAlert(
                id="alert_001",
                type="URL_ERROR",
                severity="high",
                ad_id="ad_12345",
                ad_name="Dream Home Awaits - Ohio",
                campaign_name="Custom Home Leads - Ohio",
                message="Destination URL returning 404 error",
                recommendation="Update landing page URL or check if page was moved",
                created_at=now - timedelta(hours=2),
                acknowledged=False,
            ),
            AuditAlert(
                id="alert_002",
                type="HIGH_SPEND_LOW_CONV",
                severity="high",
                ad_id="ad_23456",
                ad_name="Luxury Floor Plans",
                campaign_name="Floor Plans Showcase",
                message="High spend ($892) with only 2 leads in last 7 days",
                recommendation="Consider pausing ad or refreshing creative",
                created_at=now - timedelta(hours=5),
                acknowledged=False,
            ),
            AuditAlert(
                id="alert_003",
                type="CONTENT_MISMATCH",
                severity="medium",
                ad_id="ad_34567",
                ad_name="Build Your Dream",
                campaign_name="Schumacher - Brand Awareness Q1",
                message="Landing page content does not match ad messaging (Score: 2/5)",
                recommendation="Review ad copy alignment with landing page",
                created_at=now - timedelta(hours=12),
                acknowledged=True,
            ),
            AuditAlert(
                id="alert_004",
                type="SPEND_ANOMALY",
                severity="medium",
                ad_id="ad_45678",
                ad_name="Open House Weekend",
                campaign_name="Model Home Open Houses",
                message="Spending increased 68% compared to 7-day average",
                recommendation="Review campaign budget and targeting settings",
                created_at=now - timedelta(hours=24),
                acknowledged=False,
            ),
            AuditAlert(
                id="alert_005",
                type="HIGH_CPC",
                severity="low",
                ad_id="ad_56789",
                ad_name="Custom Designs Video",
                campaign_name="Video Tours Campaign",
                message="CPC ($2.45) is 85% higher than campaign average",
                recommendation="Review audience targeting and bid strategy",
                created_at=now - timedelta(hours=36),
                acknowledged=False,
            ),
        ]
