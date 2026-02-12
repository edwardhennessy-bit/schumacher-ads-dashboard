const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

// Types matching backend schemas
export interface MetricsOverview {
  spend: number;
  spend_change: number;
  impressions: number;
  impressions_change: number;
  clicks: number;
  clicks_change: number;
  ctr: number;
  ctr_change: number;
  cpc: number;
  cpc_change: number;
  cpm: number;
  cpm_change: number;
  conversions: number;
  conversions_change: number;
  // Lead metrics
  leads: number;
  leads_change: number;
  cost_per_lead: number;
  cost_per_lead_change: number;
  lead_rate: number;
  lead_rate_change: number;
  // Opportunity metrics
  opportunities: number;
  opportunities_change: number;
  cost_per_opportunity: number;
  cost_per_opportunity_change: number;
  // Segmented CPL metrics
  remarketing_leads: number;
  remarketing_spend: number;
  remarketing_cpl: number;
  prospecting_leads: number;
  prospecting_spend: number;
  prospecting_cpl: number;
  // Ad inventory
  active_ads: number;
  total_ads: number;
  active_ads_threshold: number;
}

export interface DailyMetric {
  date: string;
  spend: number;
  impressions: number;
  clicks: number;
  conversions: number;
  leads: number;
  ctr?: number;
  cpc?: number;
  cpm?: number;
  cost_per_lead?: number;
}

export interface Campaign {
  id: string;
  name: string;
  status: "ACTIVE" | "PAUSED" | "ARCHIVED";
  objective: string;
  spend: number;
  impressions: number;
  clicks: number;
  ctr: number;
  cpc: number;
  conversions: number;
  cost_per_conversion: number;
  // Lead metrics
  leads: number;
  cost_per_lead: number;
  lead_rate: number;
  // Opportunity metrics
  opportunities: number;
  cost_per_opportunity: number;
}

export interface AuditAlert {
  id: string;
  type: "URL_ERROR" | "CONTENT_MISMATCH" | "HIGH_SPEND_LOW_CONV" | "SPEND_ANOMALY" | "HIGH_CPC";
  severity: "high" | "medium" | "low";
  ad_id: string;
  ad_name: string;
  campaign_name: string;
  message: string;
  recommendation: string;
  created_at: string;
  acknowledged: boolean;
}

export interface AuditSummary {
  total: number;
  unacknowledged: number;
  by_severity: {
    high: number;
    medium: number;
    low: number;
  };
  by_type: Record<string, number>;
}

export interface ApiStatus {
  meta_connected: boolean;
  google_connected: boolean;
  microsoft_connected: boolean;
  claude_connected: boolean;
  slack_connected: boolean;
  database_url: string;
}

import type { DateRange } from "@/lib/date-range";

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async fetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  /** Build query string with optional date range params */
  private dateParams(dateRange?: DateRange, extra?: Record<string, string>): string {
    const params = new URLSearchParams();
    if (dateRange) {
      params.set("start_date", dateRange.startDate);
      params.set("end_date", dateRange.endDate);
    }
    if (extra) {
      for (const [k, v] of Object.entries(extra)) {
        params.set(k, v);
      }
    }
    const qs = params.toString();
    return qs ? `?${qs}` : "";
  }

  // Status
  async getStatus(): Promise<ApiStatus> {
    return this.fetch<ApiStatus>("/api/status");
  }

  // Metrics
  async getMetricsOverview(dateRange?: DateRange): Promise<MetricsOverview> {
    return this.fetch<MetricsOverview>(`/api/metrics/overview${this.dateParams(dateRange)}`);
  }

  async getTrendData(days: number = 30, dateRange?: DateRange): Promise<DailyMetric[]> {
    return this.fetch<DailyMetric[]>(
      `/api/metrics/trends${this.dateParams(dateRange, { days: String(days) })}`
    );
  }

  async getAdInventory(): Promise<{ active: number; total: number; paused: number }> {
    return this.fetch("/api/metrics/inventory");
  }

  // Campaigns
  async getCampaigns(dateRange?: DateRange): Promise<Campaign[]> {
    return this.fetch<Campaign[]>(`/api/campaigns${this.dateParams(dateRange)}`);
  }

  async getCampaign(id: string): Promise<Campaign> {
    return this.fetch<Campaign>(`/api/campaigns/${id}`);
  }

  // Audits
  async getAlerts(params?: {
    severity?: string;
    acknowledged?: boolean;
  }): Promise<AuditAlert[]> {
    const searchParams = new URLSearchParams();
    if (params?.severity) searchParams.set("severity", params.severity);
    if (params?.acknowledged !== undefined) {
      searchParams.set("acknowledged", String(params.acknowledged));
    }
    const query = searchParams.toString();
    return this.fetch<AuditAlert[]>(`/api/audits/alerts${query ? `?${query}` : ""}`);
  }

  async acknowledgeAlert(alertId: string): Promise<void> {
    await this.fetch(`/api/audits/alerts/${alertId}/acknowledge`, {
      method: "POST",
    });
  }

  async getAuditSummary(): Promise<AuditSummary> {
    return this.fetch<AuditSummary>("/api/audits/summary");
  }

  async runAudit(): Promise<{ message: string; status: string }> {
    return this.fetch("/api/audits/run", { method: "POST" });
  }

  // --- Google Ads ---
  async getGoogleOverview(dateRange?: DateRange): Promise<MetricsOverview> {
    return this.fetch<MetricsOverview>(`/api/google/overview${this.dateParams(dateRange)}`);
  }

  async getGoogleCampaigns(dateRange?: DateRange): Promise<Campaign[]> {
    return this.fetch<Campaign[]>(`/api/google/campaigns${this.dateParams(dateRange)}`);
  }

  async getGoogleTrends(days: number = 30, dateRange?: DateRange): Promise<DailyMetric[]> {
    return this.fetch<DailyMetric[]>(
      `/api/google/trends${this.dateParams(dateRange, { days: String(days) })}`
    );
  }

  async getGoogleStatus(): Promise<{ configured: boolean; customer_id: string }> {
    return this.fetch("/api/google/status");
  }
}

// Export singleton instance
export const api = new ApiClient();

// Export class for custom instances
export { ApiClient };
