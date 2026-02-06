// Mock data for Schumacher Homes Paid Media Dashboard

export interface MetricsOverview {
  spend: number;
  spendChange: number;
  impressions: number;
  impressionsChange: number;
  clicks: number;
  clicksChange: number;
  ctr: number;
  ctrChange: number;
  cpc: number;
  cpcChange: number;
  cpm: number;
  cpmChange: number;
  conversions: number;
  conversionsChange: number;
  // Lead metrics
  leads: number;
  leadsChange: number;
  costPerLead: number;
  costPerLeadChange: number;
  leadRate: number;
  leadRateChange: number;
  // Segmented CPL
  remarketingLeads: number;
  remarketingSpend: number;
  remarketingCpl: number;
  prospectingLeads: number;
  prospectingSpend: number;
  prospectingCpl: number;
  // Ad inventory
  activeAds: number;
  totalAds: number;
  activeAdsThreshold: number;
}

export interface DailyMetric {
  date: string;
  spend: number;
  impressions: number;
  clicks: number;
  conversions: number;
  leads: number;
  costPerLead?: number;
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
  costPerConversion: number;
  // Lead metrics
  leads: number;
  costPerLead: number;
  leadRate: number;
}

export interface AuditAlert {
  id: string;
  type: "URL_ERROR" | "CONTENT_MISMATCH" | "HIGH_SPEND_LOW_CONV" | "SPEND_ANOMALY" | "HIGH_CPC";
  severity: "high" | "medium" | "low";
  adId: string;
  adName: string;
  campaignName: string;
  message: string;
  recommendation: string;
  createdAt: string;
  acknowledged: boolean;
}

// Generate mock metrics overview
export const mockMetricsOverview: MetricsOverview = {
  spend: 45872.34,
  spendChange: 12.5,
  impressions: 2847593,
  impressionsChange: 8.3,
  clicks: 42847,
  clicksChange: 15.2,
  ctr: 1.50,
  ctrChange: 6.4,
  cpc: 1.07,
  cpcChange: -2.3,
  cpm: 16.11,
  cpmChange: 3.9,
  conversions: 847,
  conversionsChange: 22.1,
  // Lead metrics
  leads: 312,
  leadsChange: 18.7,
  costPerLead: 147.03,
  costPerLeadChange: -5.2,
  leadRate: 0.73,
  leadRateChange: 3.1,
  // Segmented CPL
  remarketingLeads: 120,
  remarketingSpend: 12000,
  remarketingCpl: 100.00,
  prospectingLeads: 192,
  prospectingSpend: 33872.34,
  prospectingCpl: 176.42,
  // Ad inventory
  activeAds: 47,
  totalAds: 62,
  activeAdsThreshold: 250,
};

// Generate 30 days of trend data
export const mockTrendData: DailyMetric[] = Array.from({ length: 30 }, (_, i) => {
  const date = new Date();
  date.setDate(date.getDate() - (29 - i));
  const baseSpend = 1500 + Math.random() * 500;
  const dayOfWeek = date.getDay();
  const weekendMultiplier = dayOfWeek === 0 || dayOfWeek === 6 ? 0.7 : 1;

  const spend = Math.round(baseSpend * weekendMultiplier * 100) / 100;
  const leads = Math.round((8 + Math.random() * 8) * weekendMultiplier);

  return {
    date: date.toISOString().split("T")[0],
    spend,
    impressions: Math.round((85000 + Math.random() * 30000) * weekendMultiplier),
    clicks: Math.round((1200 + Math.random() * 600) * weekendMultiplier),
    conversions: Math.round((20 + Math.random() * 20) * weekendMultiplier),
    leads,
    costPerLead: leads > 0 ? Math.round((spend / leads) * 100) / 100 : 0,
  };
});

// Mock campaigns
export const mockCampaigns: Campaign[] = [
  {
    id: "camp_001",
    name: "Schumacher - Brand Awareness Q1",
    status: "ACTIVE",
    objective: "BRAND_AWARENESS",
    spend: 12450.00,
    impressions: 892340,
    clicks: 12847,
    ctr: 1.44,
    cpc: 0.97,
    conversions: 234,
    costPerConversion: 53.21,
    leads: 45,
    costPerLead: 276.67,
    leadRate: 0.35,
  },
  {
    id: "camp_002",
    name: "Custom Home Leads - Ohio",
    status: "ACTIVE",
    objective: "LEAD_GENERATION",
    spend: 8932.50,
    impressions: 456789,
    clicks: 8234,
    ctr: 1.80,
    cpc: 1.08,
    conversions: 189,
    costPerConversion: 47.26,
    leads: 87,
    costPerLead: 102.67,
    leadRate: 1.06,
  },
  {
    id: "camp_003",
    name: "Floor Plans Showcase",
    status: "ACTIVE",
    objective: "TRAFFIC",
    spend: 6789.25,
    impressions: 523456,
    clicks: 7892,
    ctr: 1.51,
    cpc: 0.86,
    conversions: 156,
    costPerConversion: 43.52,
    leads: 52,
    costPerLead: 130.56,
    leadRate: 0.66,
  },
  {
    id: "camp_004",
    name: "Model Home Open Houses",
    status: "ACTIVE",
    objective: "ENGAGEMENT",
    spend: 5234.80,
    impressions: 345678,
    clicks: 5432,
    ctr: 1.57,
    cpc: 0.96,
    conversions: 98,
    costPerConversion: 53.42,
    leads: 34,
    costPerLead: 153.96,
    leadRate: 0.63,
  },
  {
    id: "camp_005",
    name: "Retargeting - Site Visitors",
    status: "ACTIVE",
    objective: "CONVERSIONS",
    spend: 4567.90,
    impressions: 234567,
    clicks: 4123,
    ctr: 1.76,
    cpc: 1.11,
    conversions: 112,
    costPerConversion: 40.78,
    leads: 48,
    costPerLead: 95.16,
    leadRate: 1.16,
  },
  {
    id: "camp_006",
    name: "Spring Sale 2024",
    status: "PAUSED",
    objective: "CONVERSIONS",
    spend: 3456.78,
    impressions: 187654,
    clicks: 2987,
    ctr: 1.59,
    cpc: 1.16,
    conversions: 67,
    costPerConversion: 51.59,
    leads: 23,
    costPerLead: 150.30,
    leadRate: 0.77,
  },
  {
    id: "camp_007",
    name: "Video Tours Campaign",
    status: "ACTIVE",
    objective: "VIDEO_VIEWS",
    spend: 2890.45,
    impressions: 156789,
    clicks: 2134,
    ctr: 1.36,
    cpc: 1.35,
    conversions: 45,
    costPerConversion: 64.23,
    leads: 15,
    costPerLead: 192.70,
    leadRate: 0.70,
  },
  {
    id: "camp_008",
    name: "Builder Testimonials",
    status: "PAUSED",
    objective: "ENGAGEMENT",
    spend: 1550.66,
    impressions: 98765,
    clicks: 1198,
    ctr: 1.21,
    cpc: 1.29,
    conversions: 23,
    costPerConversion: 67.42,
    leads: 8,
    costPerLead: 193.83,
    leadRate: 0.67,
  },
];

// Mock audit alerts
export const mockAuditAlerts: AuditAlert[] = [
  {
    id: "alert_001",
    type: "URL_ERROR",
    severity: "high",
    adId: "ad_12345",
    adName: "Dream Home Awaits - Ohio",
    campaignName: "Custom Home Leads - Ohio",
    message: "Destination URL returning 404 error",
    recommendation: "Update landing page URL or check if page was moved",
    createdAt: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    acknowledged: false,
  },
  {
    id: "alert_002",
    type: "HIGH_SPEND_LOW_CONV",
    severity: "high",
    adId: "ad_23456",
    adName: "Luxury Floor Plans",
    campaignName: "Floor Plans Showcase",
    message: "High spend ($892) with only 2 leads in last 7 days",
    recommendation: "Consider pausing ad or refreshing creative",
    createdAt: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
    acknowledged: false,
  },
  {
    id: "alert_003",
    type: "CONTENT_MISMATCH",
    severity: "medium",
    adId: "ad_34567",
    adName: "Build Your Dream",
    campaignName: "Schumacher - Brand Awareness Q1",
    message: "Landing page content does not match ad messaging (Score: 2/5)",
    recommendation: "Review ad copy alignment with landing page",
    createdAt: new Date(Date.now() - 12 * 60 * 60 * 1000).toISOString(),
    acknowledged: true,
  },
  {
    id: "alert_004",
    type: "SPEND_ANOMALY",
    severity: "medium",
    adId: "ad_45678",
    adName: "Open House Weekend",
    campaignName: "Model Home Open Houses",
    message: "Spending increased 68% compared to 7-day average",
    recommendation: "Review campaign budget and targeting settings",
    createdAt: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    acknowledged: false,
  },
  {
    id: "alert_005",
    type: "HIGH_CPC",
    severity: "low",
    adId: "ad_56789",
    adName: "Custom Designs Video",
    campaignName: "Video Tours Campaign",
    message: "CPC ($2.45) is 85% higher than campaign average",
    recommendation: "Review audience targeting and bid strategy",
    createdAt: new Date(Date.now() - 36 * 60 * 60 * 1000).toISOString(),
    acknowledged: false,
  },
];

// Helper to format currency
export function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(value);
}

// Helper to format large numbers
export function formatNumber(value: number): string {
  if (value >= 1000000) {
    return (value / 1000000).toFixed(1) + "M";
  }
  if (value >= 1000) {
    return (value / 1000).toFixed(1) + "K";
  }
  return value.toString();
}

// Helper to format percentage
export function formatPercent(value: number): string {
  return value.toFixed(2) + "%";
}
