# Multi-Platform Dashboard Implementation Plan

## Overview
Add Google Ads and Microsoft Ads dashboards alongside the existing Meta dashboard, plus a cross-platform overview page.

## Routes
- `/` → Cross-platform Overview (Spend, Leads, CPL per platform)
- `/meta` → Meta Dashboard (current page moved here)
- `/google` → Google Ads Dashboard (new)
- `/microsoft` → Microsoft Ads placeholder (coming soon)

## Backend Changes

### 1. New: `backend/app/services/google_ads_api.py`
- `GoogleAdsService` class using Google Ads REST API via httpx
- Customer ID: `3428920141`, MCC: `5405350977`
- Methods: `get_account_performance()`, `get_campaign_performance()`, `get_daily_performance()`
- Transforms: cost_micros÷1M, fractional conversions→leads, decimal ctr→%

### 2. New: `backend/app/routers/google_metrics.py`
- `GET /api/google/overview` — overview metrics
- `GET /api/google/campaigns` — campaign list
- `GET /api/google/trends` — daily data for charts

### 3. Modify: `backend/app/config.py`
- Add Google Ads OAuth2 credentials to Settings

### 4. Modify: `backend/app/main.py`
- Register google_metrics_router, update /api/status

## Frontend Changes

### 5. Modify: `frontend/src/lib/api.ts`
- Add: `getGoogleOverview()`, `getGoogleCampaigns()`, `getGoogleTrends()`

### 6. New: `frontend/src/app/meta/page.tsx`
- Move current page.tsx here (no logic changes)

### 7. New: `frontend/src/app/google/page.tsx`
- Same structure as Meta, calls Google endpoints
- Reuses: MetricCard, TrendChart, CampaignTable, DateRangeSelector

### 8. Rewrite: `frontend/src/app/page.tsx`
- Cross-platform overview: side-by-side Spend/Leads/CPL cards

### 9. New: `frontend/src/app/microsoft/page.tsx`
- Placeholder "Coming Soon" page

### 10. Modify: `frontend/src/components/layout/Sidebar.tsx`
- Nav: Overview, Meta, Google, Microsoft, JARVIS, Campaigns, etc.
