from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Literal


class MetricsOverview(BaseModel):
    spend: float = 0
    spend_change: float = 0
    impressions: int = 0
    impressions_change: float = 0
    clicks: int = 0
    clicks_change: float = 0
    ctr: float = 0
    ctr_change: float = 0
    cpc: float = 0
    cpc_change: float = 0
    cpm: float = 0
    cpm_change: float = 0
    conversions: int = 0
    conversions_change: float = 0
    # Lead metrics
    leads: int = 0
    leads_change: float = 0
    cost_per_lead: float = 0
    cost_per_lead_change: float = 0
    lead_rate: float = 0  # leads / clicks as percentage
    lead_rate_change: float = 0
    # Opportunity metrics (HubSpot - Opportunity)
    opportunities: int = 0
    opportunities_change: float = 0
    cost_per_opportunity: float = 0
    cost_per_opportunity_change: float = 0
    # Segmented CPL metrics
    remarketing_leads: int = 0
    remarketing_spend: float = 0
    remarketing_cpl: float = 0
    prospecting_leads: int = 0
    prospecting_spend: float = 0
    prospecting_cpl: float = 0
    # Ad inventory
    active_ads: int = 0
    total_ads: int = 0
    active_ads_threshold: int = 250


class DailyMetric(BaseModel):
    date: str
    spend: float
    impressions: int
    clicks: int
    conversions: int
    leads: int
    opportunities: int = 0
    ctr: Optional[float] = None
    cpc: Optional[float] = None
    cpm: Optional[float] = None
    cost_per_lead: Optional[float] = None
    cost_per_opportunity: Optional[float] = None


class Campaign(BaseModel):
    id: str
    name: str
    status: Literal["ACTIVE", "PAUSED", "ARCHIVED"]
    objective: str
    spend: float
    impressions: int
    clicks: int
    ctr: float
    cpc: float
    conversions: int
    cost_per_conversion: float
    # Lead metrics
    leads: int
    cost_per_lead: float
    lead_rate: float  # leads / clicks as percentage
    # Opportunity metrics
    opportunities: int = 0
    cost_per_opportunity: float = 0


class AdSet(BaseModel):
    id: str
    name: str
    campaign_id: str
    status: Literal["ACTIVE", "PAUSED", "ARCHIVED"]
    spend: float
    impressions: int
    clicks: int
    conversions: int


class Ad(BaseModel):
    id: str
    name: str
    adset_id: str
    campaign_id: str
    status: Literal["ACTIVE", "PAUSED", "ARCHIVED"]
    creative_type: str
    headline: Optional[str] = None
    body: Optional[str] = None
    destination_url: Optional[str] = None
    spend: float
    impressions: int
    clicks: int
    conversions: int


class AuditResult(BaseModel):
    id: str
    ad_id: str
    audit_type: Literal[
        "URL_HEALTH", "CONTENT_MATCH", "CREATIVE_ALIGNMENT", "PERFORMANCE"
    ]
    score: Optional[int] = None
    findings: dict
    recommendation: str
    created_at: datetime


class AuditAlert(BaseModel):
    id: str
    type: Literal[
        "URL_ERROR",
        "CONTENT_MISMATCH",
        "HIGH_SPEND_LOW_CONV",
        "SPEND_ANOMALY",
        "HIGH_CPC",
    ]
    severity: Literal["high", "medium", "low"]
    ad_id: str
    ad_name: str
    campaign_name: str
    message: str
    recommendation: str
    created_at: datetime
    acknowledged: bool = False


class URLHealthCheck(BaseModel):
    url: str
    status_code: int
    response_time_ms: int
    is_healthy: bool
    last_checked: datetime
    error_message: Optional[str] = None
