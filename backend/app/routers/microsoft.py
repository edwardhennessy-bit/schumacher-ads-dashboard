"""
Microsoft Ads Router — accepts scraped data from the frontend Chrome extension
and serves it back to the dashboard.

Since Microsoft Ads is not yet in the MCP Gateway, data is collected by the user
clicking "Scrape" which triggers a browser-based scrape via Claude in Chrome,
then POSTs the extracted metrics here for storage and serving.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import json
import os
import structlog
from datetime import datetime

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/microsoft", tags=["microsoft-ads"])

# Simple file-based store so data survives backend restarts
_DATA_FILE = os.path.join(os.path.dirname(__file__), "../../../data/microsoft_scraped.json")


def _ensure_data_dir():
    os.makedirs(os.path.dirname(_DATA_FILE), exist_ok=True)


def _load() -> dict:
    _ensure_data_dir()
    if os.path.exists(_DATA_FILE):
        try:
            with open(_DATA_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save(data: dict):
    _ensure_data_dir()
    with open(_DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


class MicrosoftScrapedMetrics(BaseModel):
    """Metrics extracted by the browser scrape from Microsoft Ads UI."""
    start_date: str
    end_date: str
    spend: float = 0
    impressions: int = 0
    clicks: int = 0
    ctr: float = 0
    cpc: float = 0
    conversions: int = 0
    cost_per_conversion: float = 0
    leads: int = 0
    cost_per_lead: float = 0
    # Optional campaign breakdown
    campaigns: list = []
    scraped_at: Optional[str] = None


class MicrosoftOverviewResponse(BaseModel):
    connected: bool = False
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
    leads: int = 0
    leads_change: float = 0
    cost_per_lead: float = 0
    cost_per_lead_change: float = 0
    conversions: int = 0
    conversions_change: float = 0
    cost_per_conversion: float = 0
    campaigns: list = []
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    scraped_at: Optional[str] = None


def _calc_change(current: float, previous: float) -> float:
    if previous == 0:
        return 0.0
    return round(((current - previous) / previous) * 100, 1)


@router.post("/ingest")
async def ingest_microsoft_data(payload: MicrosoftScrapedMetrics):
    """
    Receive scraped Microsoft Ads metrics from the frontend and store them.
    Called automatically after a successful browser scrape.
    """
    data = _load()

    # Build a cache key for this date range so different ranges are stored separately
    range_key = f"{payload.start_date}__{payload.end_date}"

    entry = payload.dict()
    entry["scraped_at"] = datetime.utcnow().isoformat()

    data[range_key] = entry

    # Always keep a "latest" entry for quick access
    data["latest"] = entry

    _save(data)

    logger.info(
        "microsoft_data_ingested",
        start_date=payload.start_date,
        end_date=payload.end_date,
        spend=payload.spend,
        leads=payload.leads,
    )

    return {"success": True, "message": "Microsoft Ads data saved", "range_key": range_key}


@router.get("/overview", response_model=MicrosoftOverviewResponse)
async def get_microsoft_overview(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """
    Return stored Microsoft Ads metrics for the requested date range.
    Falls back to the most recently scraped data if no exact match.
    """
    data = _load()

    if not data:
        return MicrosoftOverviewResponse(connected=False)

    # Try exact date range match first
    entry = None
    if start_date and end_date:
        range_key = f"{start_date}__{end_date}"
        entry = data.get(range_key)

    # Fall back to latest
    if not entry:
        entry = data.get("latest")

    if not entry:
        return MicrosoftOverviewResponse(connected=False)

    return MicrosoftOverviewResponse(
        connected=True,
        spend=entry.get("spend", 0),
        impressions=entry.get("impressions", 0),
        clicks=entry.get("clicks", 0),
        ctr=entry.get("ctr", 0),
        cpc=entry.get("cpc", 0),
        leads=entry.get("leads", 0),
        cost_per_lead=entry.get("cost_per_lead", 0),
        conversions=entry.get("conversions", 0),
        cost_per_conversion=entry.get("cost_per_conversion", 0),
        campaigns=entry.get("campaigns", []),
        start_date=entry.get("start_date"),
        end_date=entry.get("end_date"),
        scraped_at=entry.get("scraped_at"),
    )


@router.delete("/clear")
async def clear_microsoft_data():
    """Clear all stored Microsoft Ads scraped data."""
    _ensure_data_dir()
    if os.path.exists(_DATA_FILE):
        os.remove(_DATA_FILE)
    return {"success": True, "message": "Microsoft Ads data cleared"}


@router.get("/status")
async def get_microsoft_status():
    """Check whether any Microsoft Ads data has been scraped."""
    data = _load()
    latest = data.get("latest")
    return {
        "has_data": latest is not None,
        "scraped_at": latest.get("scraped_at") if latest else None,
        "date_range": f"{latest.get('start_date')} → {latest.get('end_date')}" if latest else None,
    }
