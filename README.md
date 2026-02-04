# Schumacher Homes Paid Media Intelligence Dashboard

A centralized web application for monitoring, analyzing, and optimizing Schumacher Homes paid media performance.

## Project Structure

```
schumacher-dashboard/
├── frontend/          # Next.js 16 + TypeScript + Tailwind + Shadcn
├── backend/           # FastAPI Python backend
└── PLAN.md           # Detailed implementation plan
```

## Quick Start

### Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at http://localhost:3000

### Backend (FastAPI)

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API will be available at http://localhost:8000

API docs at http://localhost:8000/docs

## Current Status

**Demo Mode** - The dashboard currently uses mock data while the Schumacher Homes Meta Ads account is being connected to the MCP Gateway.

### Completed Features

- Dashboard layout with sidebar navigation
- Metric cards (Spend, Impressions, Clicks, CTR, CPC, Active Ads)
- 30-day performance trend chart
- Campaign performance table
- Audit alerts feed with acknowledge functionality
- FastAPI backend with mock data endpoints

### Pending Features

- Real Meta Ads integration (requires account connection)
- Smart audit agent (URL health checks, content matching)
- Slack notifications
- Database persistence

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/metrics/overview` | GET | Dashboard metrics overview |
| `/api/metrics/trends` | GET | Daily trend data |
| `/api/metrics/inventory` | GET | Active/paused ad counts |
| `/api/campaigns` | GET | List all campaigns |
| `/api/campaigns/{id}` | GET | Single campaign details |
| `/api/audits/alerts` | GET | List audit alerts |
| `/api/audits/alerts/{id}/acknowledge` | POST | Acknowledge an alert |
| `/api/audits/summary` | GET | Alert summary stats |

## Environment Variables

Copy `.env.example` to `.env` in the backend directory:

```bash
cp backend/.env.example backend/.env
```

Required variables:
- `META_AD_ACCOUNT_ID` - Meta Ads account ID (when connected)
- `ANTHROPIC_API_KEY` - Claude API key for smart audits
- `SLACK_WEBHOOK_URL` - Slack webhook for notifications

## Next Steps

1. Connect Schumacher Homes Meta Ads account to MCP Gateway
2. Replace mock data service with real Meta Ads integration
3. Implement URL health checking service
4. Build Claude-powered content matching audits
5. Add Slack notification integration
