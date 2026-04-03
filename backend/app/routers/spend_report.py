"""
Spend Report router
POST /api/reports/spend-report/generate  → kicks off the agent in a background thread
GET  /api/reports/spend-report/status/{job_id} → poll for progress / result
"""
from __future__ import annotations

import subprocess
import sys
import threading
import uuid
from pathlib import Path
from typing import Optional

import structlog
from fastapi import APIRouter
from pydantic import BaseModel

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/reports", tags=["spend-report"])

# Absolute path to the spend-agent project (sibling of this repo)
SPEND_AGENT_DIR = Path.home() / "ClaudeCode" / "schumacher-spend-agent"
SPEND_AGENT_SCRIPT = SPEND_AGENT_DIR / "spend_agent.py"

# In-memory job store — fine for a single-user dashboard
_jobs: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class SpendReportRequest(BaseModel):
    google_hubspot: float
    microsoft_hubspot: float
    meta_hubspot: float
    month: Optional[str] = None           # e.g. "March 2026"; omit to auto-detect prior month
    location_notes: Optional[str] = None  # any location changes the user described


# ---------------------------------------------------------------------------
# Background worker
# ---------------------------------------------------------------------------

def _run_agent(job_id: str, request: SpendReportRequest, output_dir: Path) -> None:
    """Blocking function — runs in a daemon thread."""
    _jobs[job_id]["status"] = "running"
    logger.info("spend_report_started", job_id=job_id)

    cmd = [
        sys.executable,
        str(SPEND_AGENT_SCRIPT),
        "--auto",
        "--skip-location-check",           # location check handled by the dashboard UI
        "--google-hubspot",    str(request.google_hubspot),
        "--microsoft-hubspot", str(request.microsoft_hubspot),
        "--meta-hubspot",      str(request.meta_hubspot),
        "--output",            str(output_dir),
    ]
    if request.month:
        cmd += ["--month", request.month]
    if request.location_notes:
        cmd += ["--location-notes", request.location_notes]

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=str(SPEND_AGENT_DIR),
        )

        log_lines: list[str] = []
        url: Optional[str] = None

        for line in proc.stdout:                         # type: ignore[union-attr]
            log_lines.append(line)
            # Capture the Google Sheets URL as soon as it appears
            if "docs.google.com/spreadsheets" in line:
                url = line.strip()
            # Flush logs to the job store after every line so the frontend
            # can show incremental progress while the agent is still running.
            _jobs[job_id]["logs"] = "".join(log_lines)

        proc.wait(timeout=600)

        _jobs[job_id]["logs"] = "".join(log_lines)

        if proc.returncode == 0:
            _jobs[job_id]["status"] = "done"
            _jobs[job_id]["url"] = url
            logger.info("spend_report_done", job_id=job_id, url=url)
        else:
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["error"] = f"Agent exited with code {proc.returncode}"
            logger.error("spend_report_failed", job_id=job_id, code=proc.returncode)

    except subprocess.TimeoutExpired:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = "Timed out after 10 minutes"
        logger.error("spend_report_timeout", job_id=job_id)
    except Exception as exc:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = str(exc)
        logger.error("spend_report_exception", job_id=job_id, error=str(exc))


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/spend-report/generate")
async def generate_spend_report(request: SpendReportRequest):
    """
    Start an async spend-report generation job.
    Returns immediately with a job_id the client can poll.
    """
    job_id = uuid.uuid4().hex[:8]
    output_dir = SPEND_AGENT_DIR / "output" / f"report-{job_id}"

    _jobs[job_id] = {
        "status": "queued",
        "logs": "",
        "url": None,
        "error": None,
    }

    thread = threading.Thread(
        target=_run_agent,
        args=(job_id, request, output_dir),
        daemon=True,
    )
    thread.start()

    logger.info("spend_report_queued", job_id=job_id)
    return {"job_id": job_id}


@router.get("/spend-report/status/{job_id}")
async def get_spend_report_status(job_id: str):
    """Poll this endpoint every 2 s while status is 'queued' or 'running'."""
    if job_id not in _jobs:
        return {"job_id": job_id, "status": "not_found", "logs": "", "url": None, "error": None}
    job = _jobs[job_id]
    return {
        "job_id": job_id,
        "status": job["status"],
        "logs":   job["logs"],
        "url":    job["url"],
        "error":  job["error"],
    }
