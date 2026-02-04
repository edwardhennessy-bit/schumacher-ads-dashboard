from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from app.models.schemas import AuditAlert
from app.services.mock_data import MockDataService

router = APIRouter(prefix="/api/audits", tags=["audits"])
mock_service = MockDataService()

# In-memory store for acknowledged alerts (will be replaced with DB)
acknowledged_alerts: set = set()


@router.get("/alerts", response_model=List[AuditAlert])
async def list_alerts(
    severity: Optional[str] = Query(default=None, pattern="^(high|medium|low)$"),
    acknowledged: Optional[bool] = None,
):
    """List all audit alerts with optional filtering."""
    alerts = mock_service.get_audit_alerts()

    # Apply acknowledged state from memory
    for alert in alerts:
        if alert.id in acknowledged_alerts:
            alert.acknowledged = True

    # Filter by severity if provided
    if severity:
        alerts = [a for a in alerts if a.severity == severity]

    # Filter by acknowledged state if provided
    if acknowledged is not None:
        alerts = [a for a in alerts if a.acknowledged == acknowledged]

    return alerts


@router.get("/alerts/{alert_id}", response_model=AuditAlert)
async def get_alert(alert_id: str):
    """Get a single alert by ID."""
    alerts = mock_service.get_audit_alerts()
    for alert in alerts:
        if alert.id == alert_id:
            if alert.id in acknowledged_alerts:
                alert.acknowledged = True
            return alert
    raise HTTPException(status_code=404, detail="Alert not found")


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    """Acknowledge an alert."""
    alerts = mock_service.get_audit_alerts()
    for alert in alerts:
        if alert.id == alert_id:
            acknowledged_alerts.add(alert_id)
            return {"message": "Alert acknowledged", "alert_id": alert_id}
    raise HTTPException(status_code=404, detail="Alert not found")


@router.post("/run")
async def run_audit():
    """Trigger a new audit (placeholder for future implementation)."""
    return {
        "message": "Audit scheduled",
        "status": "pending",
        "note": "Full audit functionality will be implemented when Meta Ads account is connected",
    }


@router.get("/summary")
async def get_audit_summary():
    """Get summary of audit alerts."""
    alerts = mock_service.get_audit_alerts()

    # Apply acknowledged state
    for alert in alerts:
        if alert.id in acknowledged_alerts:
            alert.acknowledged = True

    return {
        "total": len(alerts),
        "unacknowledged": len([a for a in alerts if not a.acknowledged]),
        "by_severity": {
            "high": len([a for a in alerts if a.severity == "high"]),
            "medium": len([a for a in alerts if a.severity == "medium"]),
            "low": len([a for a in alerts if a.severity == "low"]),
        },
        "by_type": {
            "URL_ERROR": len([a for a in alerts if a.type == "URL_ERROR"]),
            "CONTENT_MISMATCH": len([a for a in alerts if a.type == "CONTENT_MISMATCH"]),
            "HIGH_SPEND_LOW_CONV": len([a for a in alerts if a.type == "HIGH_SPEND_LOW_CONV"]),
            "SPEND_ANOMALY": len([a for a in alerts if a.type == "SPEND_ANOMALY"]),
            "HIGH_CPC": len([a for a in alerts if a.type == "HIGH_CPC"]),
        },
    }
