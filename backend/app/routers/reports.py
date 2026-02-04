"""
Reports router for generating CSV exports and reports.
"""

import csv
import io
import json
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/reports", tags=["reports"])

DATA_DIR = Path(__file__).parent.parent.parent / "data"


@router.get("/active-ads/csv")
async def export_active_ads_csv():
    """
    Export all truly active ads (effective_status=ACTIVE) to CSV.
    Includes ad name, campaign, ad set, and metrics.
    """
    # Load active ads data
    active_ads_file = DATA_DIR / "active_ads.json"
    campaigns_file = DATA_DIR / "campaigns.json"

    if not active_ads_file.exists():
        return {"error": "Active ads data not available. Please refresh data first."}

    with open(active_ads_file, "r") as f:
        active_ads = json.load(f)

    # Load campaigns for name lookup
    campaign_names = {}
    if campaigns_file.exists():
        with open(campaigns_file, "r") as f:
            campaigns = json.load(f)
            campaign_names = {c["id"]: c["name"] for c in campaigns}

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    writer.writerow([
        "Ad ID",
        "Ad Name",
        "Campaign ID",
        "Campaign Name",
        "Ad Set ID",
        "Status",
        "Created Date"
    ])

    # Data rows
    for ad in active_ads:
        campaign_name = campaign_names.get(ad.get("campaign_id", ""), "Unknown")
        created_time = ad.get("created_time", "")
        if created_time:
            # Parse and format the date
            try:
                dt = datetime.fromisoformat(created_time.replace("Z", "+00:00"))
                created_time = dt.strftime("%Y-%m-%d %H:%M")
            except:
                pass

        writer.writerow([
            ad.get("id", ""),
            ad.get("name", ""),
            ad.get("campaign_id", ""),
            campaign_name,
            ad.get("adset_id", ""),
            ad.get("status", "ACTIVE"),
            created_time
        ])

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"schumacher_active_ads_{timestamp}.csv"

    # Return as streaming response
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/active-ads/summary")
async def get_active_ads_summary():
    """Get summary of active ads for display."""
    active_ads_file = DATA_DIR / "active_ads.json"

    if not active_ads_file.exists():
        return {"count": 0, "ads": []}

    with open(active_ads_file, "r") as f:
        active_ads = json.load(f)

    return {
        "count": len(active_ads),
        "last_updated": datetime.now().isoformat(),
        "ads": active_ads[:10]  # Return first 10 for preview
    }
