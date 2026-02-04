# Schumacher Homes Paid Media Intelligence Dashboard - Implementation Plan

## Project Overview

A centralized web application and AI agent to monitor, analyze, and optimize Schumacher Homes paid media performance, starting with Meta Ads.

**Target Location:** `~/ClaudeCode/schumacher-dashboard`

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (Next.js)                       │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌────────────┐ │
│  │ Dashboard   │ │ Campaign    │ │ Audit Feed  │ │ Settings   │ │
│  │ Overview    │ │ Details     │ │ & Alerts    │ │ Panel      │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Backend API (FastAPI)                       │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌────────────┐ │
│  │ /api/       │ │ /api/       │ │ /api/       │ │ /api/      │ │
│  │ metrics     │ │ campaigns   │ │ audits      │ │ alerts     │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│  MCP Gateway     │ │  Claude API      │ │  SQLite DB       │
│  (Meta Ads API)  │ │  (Audit Agent)   │ │  (Cache/History) │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

---

## Phase 1: Foundation & Meta Ads Dashboard

### 1.1 Project Setup

**Files to create:**
```
schumacher-dashboard/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app entry
│   │   ├── config.py            # Settings & env vars
│   │   ├── dependencies.py      # Shared dependencies
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── metrics.py       # Performance metrics endpoints
│   │   │   ├── campaigns.py     # Campaign/AdSet/Ad endpoints
│   │   │   ├── audits.py        # Audit results endpoints
│   │   │   └── alerts.py        # Alerts & notifications
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── meta_ads.py      # MCP Gateway integration
│   │   │   ├── audit_agent.py   # Smart audit logic
│   │   │   └── url_checker.py   # URL validation service
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── schemas.py       # Pydantic models
│   │   │   └── database.py      # SQLAlchemy models
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── helpers.py
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx         # Dashboard home
│   │   │   ├── campaigns/
│   │   │   │   └── page.tsx     # Campaign details
│   │   │   └── audits/
│   │   │       └── page.tsx     # Audit feed
│   │   ├── components/
│   │   │   ├── ui/              # Shadcn components
│   │   │   ├── dashboard/
│   │   │   │   ├── MetricCard.tsx
│   │   │   │   ├── TrendChart.tsx
│   │   │   │   ├── AdInventory.tsx
│   │   │   │   └── AlertsFeed.tsx
│   │   │   └── layout/
│   │   │       ├── Header.tsx
│   │   │       ├── Sidebar.tsx
│   │   │       └── DateRangePicker.tsx
│   │   ├── lib/
│   │   │   ├── api.ts           # API client
│   │   │   └── utils.ts
│   │   └── hooks/
│   │       └── useMetrics.ts
│   ├── package.json
│   ├── tailwind.config.js
│   └── next.config.js
├── docker-compose.yml
└── README.md
```

### 1.2 Backend API Endpoints

#### Metrics Router (`/api/metrics`)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/metrics/overview` | GET | High-level stats (spend, impressions, CTR, CPC, CPM) |
| `/api/metrics/trends` | GET | Daily/weekly trend data for charts |
| `/api/metrics/inventory` | GET | Active vs. Paused ad counts |

#### Campaigns Router (`/api/campaigns`)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/campaigns` | GET | List all campaigns with insights |
| `/api/campaigns/{id}` | GET | Single campaign details |
| `/api/campaigns/{id}/adsets` | GET | Ad sets within campaign |
| `/api/campaigns/{id}/ads` | GET | Ads within campaign |

#### Audits Router (`/api/audits`)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/audits` | GET | List all audit results |
| `/api/audits/run` | POST | Trigger a new audit |
| `/api/audits/{id}` | GET | Single audit details |

### 1.3 MCP Gateway Integration

The backend will call the MCP Gateway tools via subprocess or HTTP:

```python
# services/meta_ads.py
class MetaAdsService:
    def __init__(self, ad_account_id: str):
        self.ad_account_id = ad_account_id

    async def get_account_insights(self, start_date: str, end_date: str):
        # Calls: meta_account_insights
        pass

    async def get_campaigns(self):
        # Calls: meta_list_campaigns
        pass

    async def get_campaign_report(self, start_date: str, end_date: str):
        # Calls: meta_campaign_report
        pass

    async def get_ads(self, campaign_id: str = None):
        # Calls: meta_list_ads
        pass
```

### 1.4 Frontend Components

#### Dashboard Layout
```
┌─────────────────────────────────────────────────────────────┐
│ [Logo]  Schumacher Ads Dashboard    [Date Range] [Refresh] │
├────────┬────────────────────────────────────────────────────┤
│        │ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
│  Nav   │ │  Spend   │ │   CTR    │ │   CPC    │ │  Ads   │ │
│        │ │ $XX,XXX  │ │  X.XX%   │ │  $X.XX   │ │ XX/YY  │ │
│ • Dash │ └──────────┘ └──────────┘ └──────────┘ └────────┘ │
│ • Camp │ ┌─────────────────────────────────────────────────┤
│ • Audit│ │                                                 │
│ • Alert│ │         Spend & Performance Trend Chart         │
│        │ │                                                 │
│        │ └─────────────────────────────────────────────────┤
│        │ ┌──────────────────────┐ ┌───────────────────────┐│
│        │ │   Campaign Table     │ │    Audit Alerts       ││
│        │ │   (sortable/filter)  │ │    (recent issues)    ││
│        │ └──────────────────────┘ └───────────────────────┘│
└────────┴────────────────────────────────────────────────────┘
```

#### Key Metric Cards
- **Spend**: Total spend with % change indicator
- **CTR**: Click-through rate with trend
- **CPC**: Cost per click
- **CPM**: Cost per 1000 impressions
- **Live Ads**: Active / Total count

---

## Phase 2: Smart Audit Agent

### 2.1 Audit Types

| Audit Type | Description | Priority |
|------------|-------------|----------|
| URL Health | Check destination URLs return 200 OK | High |
| URL-Content Match | Landing page content matches ad intent | High |
| Copy-Creative Alignment | Text copy matches image/video theme | Medium |
| Performance Flags | High spend / Low conversion detection | High |
| Spend Anomalies | Unusual spending spikes or drops | Medium |

### 2.2 URL Validation Service

```python
# services/url_checker.py
class URLChecker:
    async def check_url_health(self, url: str) -> URLHealthResult:
        """Ping URL, return status code and response time"""
        pass

    async def scrape_landing_page(self, url: str) -> LandingPageContent:
        """Extract text, meta tags, key elements from landing page"""
        pass

    async def validate_content_match(
        self,
        ad_copy: str,
        landing_content: LandingPageContent
    ) -> ContentMatchResult:
        """Use Claude to assess if landing page matches ad intent"""
        pass
```

### 2.3 Claude Audit Prompts

**URL-Content Match Audit:**
```
You are a paid media quality auditor. Analyze if this landing page
matches the ad's intent.

Ad Headline: {headline}
Ad Body: {body_text}
Ad CTA: {cta_text}

Landing Page Title: {page_title}
Landing Page H1: {page_h1}
Landing Page Content: {page_content_excerpt}

Rate the match from 1-5:
5 = Perfect match
4 = Good match, minor differences
3 = Partial match, some disconnect
2 = Poor match, significant mismatch
1 = Complete mismatch

Respond in JSON: { "score": X, "reasoning": "...", "recommendation": "..." }
```

**Copy-Creative Alignment:**
```
You are analyzing ad creative alignment. Given the ad copy and
image description, assess if they work together cohesively.

Ad Copy: {copy}
Image Description: {image_description}
Product/Service: {product_context}

Rate alignment from 1-5 and provide specific feedback.
```

### 2.4 Performance Flagging Logic

```python
# services/audit_agent.py
class AuditAgent:
    def flag_underperformers(self, ads: List[Ad]) -> List[AuditFlag]:
        flags = []
        for ad in ads:
            # High Spend + Low Conversions
            if ad.spend > threshold_spend and ad.conversions < threshold_conv:
                flags.append(AuditFlag(
                    type="HIGH_SPEND_LOW_CONV",
                    ad_id=ad.id,
                    severity="high",
                    recommendation="Consider pausing or refreshing creative"
                ))

            # High CPC outliers
            if ad.cpc > (avg_cpc * 1.5):
                flags.append(AuditFlag(
                    type="HIGH_CPC",
                    ad_id=ad.id,
                    severity="medium",
                    recommendation="Review targeting and bid strategy"
                ))
        return flags
```

### 2.5 Standing Notifications (Heartbeat)

Background job that runs every 4 hours:
1. Check all destination URLs for 4xx/5xx errors
2. Detect spending anomalies (>50% daily change)
3. Flag any newly paused high-spend campaigns
4. Send Slack alerts for critical issues

---

## Phase 3: Database Schema

### Tables

```sql
-- Cache Meta Ads data for faster dashboard loads
CREATE TABLE cached_metrics (
    id INTEGER PRIMARY KEY,
    account_id TEXT NOT NULL,
    date DATE NOT NULL,
    spend DECIMAL(10,2),
    impressions INTEGER,
    clicks INTEGER,
    conversions INTEGER,
    ctr DECIMAL(5,4),
    cpc DECIMAL(10,4),
    cpm DECIMAL(10,4),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(account_id, date)
);

-- Audit results history
CREATE TABLE audits (
    id INTEGER PRIMARY KEY,
    ad_id TEXT NOT NULL,
    audit_type TEXT NOT NULL,
    score INTEGER,
    severity TEXT,
    findings TEXT,  -- JSON
    recommendation TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- URL health checks
CREATE TABLE url_checks (
    id INTEGER PRIMARY KEY,
    url TEXT NOT NULL,
    ad_id TEXT,
    status_code INTEGER,
    response_time_ms INTEGER,
    is_healthy BOOLEAN,
    last_checked TIMESTAMP,
    UNIQUE(url)
);

-- Alerts sent
CREATE TABLE alerts (
    id INTEGER PRIMARY KEY,
    alert_type TEXT NOT NULL,
    ad_id TEXT,
    campaign_id TEXT,
    message TEXT,
    severity TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    acknowledged BOOLEAN DEFAULT FALSE
);
```

---

## Implementation Order

### Week 1: Foundation
- [ ] Initialize Next.js frontend with Tailwind + Shadcn
- [ ] Initialize FastAPI backend with project structure
- [ ] Set up MCP Gateway integration service
- [ ] Create basic API endpoints for metrics
- [ ] Build dashboard layout with placeholder data

### Week 2: Meta Ads Integration
- [ ] Implement all Meta Ads API service methods
- [ ] Build metrics overview endpoint with real data
- [ ] Create trend charts with date range filtering
- [ ] Implement campaign listing with insights
- [ ] Add ad inventory counts

### Week 3: Smart Audit - Phase 1
- [ ] Build URL health checker service
- [ ] Implement landing page scraper (Playwright)
- [ ] Create Claude integration for content matching
- [ ] Build audit results storage
- [ ] Create audit feed UI component

### Week 4: Smart Audit - Phase 2 & Polish
- [ ] Implement performance flagging logic
- [ ] Build Slack notification integration
- [ ] Add background job scheduler (heartbeat)
- [ ] Polish UI, add loading states, error handling
- [ ] Performance optimization for <2s load times

---

## Configuration Requirements

### Environment Variables
```env
# Meta Ads (via MCP Gateway)
META_AD_ACCOUNT_ID=act_XXXXXXXXXX

# Claude API
ANTHROPIC_API_KEY=sk-ant-xxxxx

# Slack Notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx

# Database
DATABASE_URL=sqlite:///./data/dashboard.db

# App Settings
AUDIT_INTERVAL_HOURS=4
SPEND_ANOMALY_THRESHOLD=0.5
```

### Account Access Note
**IMPORTANT:** The Schumacher Homes Meta Ads account is not currently visible in the MCP Gateway. Before implementation, we need to either:
1. Connect the Schumacher Homes account to the MCP Gateway
2. Use a placeholder/demo account for development, then switch when access is granted

---

## Success Metrics Tracking

| Metric | Target | Measurement |
|--------|--------|-------------|
| URL Mismatch Accuracy | 95%+ | Manual validation of flagged mismatches |
| Manual Audit Time Reduction | 80% | Time comparison before/after |
| Dashboard Load Time | <2 seconds | Performance monitoring for 30-day views |

---

## Next Steps

1. **Confirm Meta Ads account access** - Need Schumacher Homes account connected to Gateway
2. **Initialize project** - Create backend/frontend scaffolding
3. **Start with metrics** - Get basic dashboard showing real data
4. **Iterate on audits** - Build audit features incrementally
