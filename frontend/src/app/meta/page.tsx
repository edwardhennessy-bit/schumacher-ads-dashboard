"use client";

import { useState, useEffect, useCallback } from "react";
import { Header } from "@/components/layout/Header";
import { MetricCard } from "@/components/dashboard/MetricCard";
import { TrendChart } from "@/components/dashboard/TrendChart";
import { CampaignTable } from "@/components/dashboard/CampaignTable";
import { AlertsFeed } from "@/components/dashboard/AlertsFeed";
import {
  DollarSign,
  MousePointer,
  Eye,
  Target,
  TrendingUp,
  Layers,
  Users,
  UserPlus,
  RefreshCw,
  Megaphone,
} from "lucide-react";
import {
  mockMetricsOverview,
  mockTrendData,
  mockCampaigns,
  mockAuditAlerts,
  formatCurrency,
  formatNumber,
  formatPercent,
} from "@/lib/mock-data";
import { api, MetricsOverview, DailyMetric, Campaign, AuditAlert } from "@/lib/api";
import {
  DateRange,
  DEFAULT_PRESET,
  getPresetByValue,
  formatDateRangeLabel,
} from "@/lib/date-range";

// Transform API response to match frontend types
function transformMetrics(apiMetrics: MetricsOverview) {
  return {
    spend: apiMetrics.spend,
    spendChange: apiMetrics.spend_change,
    impressions: apiMetrics.impressions,
    impressionsChange: apiMetrics.impressions_change,
    clicks: apiMetrics.clicks,
    clicksChange: apiMetrics.clicks_change,
    ctr: apiMetrics.ctr,
    ctrChange: apiMetrics.ctr_change,
    cpc: apiMetrics.cpc,
    cpcChange: apiMetrics.cpc_change,
    cpm: apiMetrics.cpm,
    cpmChange: apiMetrics.cpm_change,
    conversions: apiMetrics.conversions,
    conversionsChange: apiMetrics.conversions_change,
    // Lead metrics
    leads: apiMetrics.leads,
    leadsChange: apiMetrics.leads_change,
    costPerLead: apiMetrics.cost_per_lead,
    costPerLeadChange: apiMetrics.cost_per_lead_change,
    leadRate: apiMetrics.lead_rate,
    leadRateChange: apiMetrics.lead_rate_change,
    // Segmented CPL
    remarketingLeads: apiMetrics.remarketing_leads,
    remarketingSpend: apiMetrics.remarketing_spend,
    remarketingCpl: apiMetrics.remarketing_cpl,
    prospectingLeads: apiMetrics.prospecting_leads,
    prospectingSpend: apiMetrics.prospecting_spend,
    prospectingCpl: apiMetrics.prospecting_cpl,
    // Ad inventory
    activeAds: apiMetrics.active_ads,
    totalAds: apiMetrics.total_ads,
    activeAdsThreshold: apiMetrics.active_ads_threshold,
  };
}

function transformTrend(t: DailyMetric) {
  return {
    date: t.date,
    spend: t.spend,
    impressions: t.impressions,
    clicks: t.clicks,
    conversions: t.conversions,
    leads: t.leads,
    costPerLead: t.cost_per_lead,
  };
}

function transformCampaign(c: Campaign) {
  return {
    id: c.id,
    name: c.name,
    status: c.status,
    objective: c.objective,
    spend: c.spend,
    impressions: c.impressions,
    clicks: c.clicks,
    ctr: c.ctr,
    cpc: c.cpc,
    conversions: c.conversions,
    costPerConversion: c.cost_per_conversion,
    // Lead metrics
    leads: c.leads,
    costPerLead: c.cost_per_lead,
    leadRate: c.lead_rate,
  };
}

function transformAlert(a: AuditAlert) {
  return {
    id: a.id,
    type: a.type,
    severity: a.severity,
    adId: a.ad_id,
    adName: a.ad_name,
    campaignName: a.campaign_name,
    message: a.message,
    recommendation: a.recommendation,
    createdAt: a.created_at,
    acknowledged: a.acknowledged,
  };
}

export default function DashboardPage() {
  const [metrics, setMetrics] = useState(mockMetricsOverview);
  const [trends, setTrends] = useState(mockTrendData);
  const [campaigns, setCampaigns] = useState(mockCampaigns);
  const [alerts, setAlerts] = useState(mockAuditAlerts);
  const [isLoading, setIsLoading] = useState(false);
  const [apiConnected, setApiConnected] = useState(false);

  // Date range state
  const [selectedPreset, setSelectedPreset] = useState(DEFAULT_PRESET);
  const [customRange, setCustomRange] = useState<DateRange | null>(null);

  /** Resolve the active date range (custom or from preset) */
  const getActiveDateRange = useCallback((): DateRange => {
    if (customRange) return customRange;
    const preset = getPresetByValue(selectedPreset);
    return preset ? preset.getRange() : getPresetByValue(DEFAULT_PRESET)!.getRange();
  }, [customRange, selectedPreset]);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    const dateRange = getActiveDateRange();
    try {
      const [metricsRes, trendsRes, campaignsRes, alertsRes] = await Promise.all([
        api.getMetricsOverview(dateRange),
        api.getTrendData(365, dateRange),
        api.getCampaigns(dateRange),
        api.getAlerts(),
      ]);

      setMetrics(transformMetrics(metricsRes));
      setTrends(trendsRes.map(transformTrend));
      setCampaigns(campaignsRes.map(transformCampaign));
      setAlerts(alertsRes.map(transformAlert));
      setApiConnected(true);
    } catch (error) {
      console.log("API not available, using mock data:", error);
      setApiConnected(false);
    } finally {
      setIsLoading(false);
    }
  }, [getActiveDateRange]);

  // Fetch on mount and when date range changes
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handlePresetChange = (preset: string) => {
    setSelectedPreset(preset);
    setCustomRange(null); // clear custom when preset selected
  };

  const handleCustomRangeChange = (range: DateRange) => {
    setCustomRange(range);
  };

  const handleRefresh = () => {
    fetchData();
  };

  const handleAcknowledge = async (alertId: string) => {
    try {
      if (apiConnected) {
        await api.acknowledgeAlert(alertId);
      }
      setAlerts((prev) =>
        prev.map((alert) =>
          alert.id === alertId ? { ...alert, acknowledged: true } : alert
        )
      );
    } catch (error) {
      console.error("Failed to acknowledge alert:", error);
    }
  };

  // Dynamic chart title
  const chartTitle = `${formatDateRangeLabel(selectedPreset, customRange)} Performance Trends`;

  return (
    <div className="min-h-screen bg-background">
      <Header
        title="Dashboard"
        subtitle={`Meta Ads Performance Overview${!apiConnected ? " (Demo Mode)" : ""}`}
        onRefresh={handleRefresh}
        isLoading={isLoading}
        selectedPreset={selectedPreset}
        customRange={customRange}
        onPresetChange={handlePresetChange}
        onCustomRangeChange={handleCustomRangeChange}
      />

      <div className="p-6 space-y-6">
        {/* Lead Metrics Row - Highlighted */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          <MetricCard
            title="Total Leads"
            value={formatNumber(metrics.leads)}
            change={metrics.leadsChange}
            icon={<UserPlus className="h-4 w-4" />}
            className="border-2 border-green-200 bg-green-50/50"
          />
          <MetricCard
            title="Blended CPL"
            value={formatCurrency(metrics.costPerLead)}
            change={metrics.costPerLeadChange}
            invertTrend
            icon={<Users className="h-4 w-4" />}
            className="border-2 border-green-200 bg-green-50/50"
          />
          <MetricCard
            title="Remarketing CPL"
            value={formatCurrency(metrics.remarketingCpl || 0)}
            subtitle={`${formatNumber(metrics.remarketingLeads || 0)} leads`}
            icon={<RefreshCw className="h-4 w-4" />}
            className="border-2 border-blue-200 bg-blue-50/50"
          />
          <MetricCard
            title="Prospecting CPL"
            value={formatCurrency(metrics.prospectingCpl || 0)}
            subtitle={`${formatNumber(metrics.prospectingLeads || 0)} leads`}
            icon={<Megaphone className="h-4 w-4" />}
            className="border-2 border-purple-200 bg-purple-50/50"
          />
          <MetricCard
            title="Active Ads"
            value={`${metrics.activeAds} / ${metrics.activeAdsThreshold || 250}`}
            subtitle={metrics.activeAds >= (metrics.activeAdsThreshold || 250) ? "At threshold!" : `${(metrics.activeAdsThreshold || 250) - metrics.activeAds} remaining`}
            icon={<Layers className="h-4 w-4" />}
            className={metrics.activeAds >= (metrics.activeAdsThreshold || 250) * 0.9
              ? "border-2 border-red-200 bg-red-50/50"
              : "border-2 border-gray-200"}
          />
        </div>

        {/* Standard Metric Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
          <MetricCard
            title="Total Spend"
            value={formatCurrency(metrics.spend)}
            change={metrics.spendChange}
            icon={<DollarSign className="h-4 w-4" />}
          />
          <MetricCard
            title="Impressions"
            value={formatNumber(metrics.impressions)}
            change={metrics.impressionsChange}
            icon={<Eye className="h-4 w-4" />}
          />
          <MetricCard
            title="Clicks"
            value={formatNumber(metrics.clicks)}
            change={metrics.clicksChange}
            icon={<MousePointer className="h-4 w-4" />}
          />
          <MetricCard
            title="CTR"
            value={formatPercent(metrics.ctr)}
            change={metrics.ctrChange}
            icon={<TrendingUp className="h-4 w-4" />}
          />
          <MetricCard
            title="CPC"
            value={formatCurrency(metrics.cpc)}
            change={metrics.cpcChange}
            invertTrend
            icon={<Target className="h-4 w-4" />}
          />
        </div>

        {/* Trend Chart */}
        <TrendChart data={trends} title={chartTitle} />

        {/* Campaign Table — Full Width */}
        <CampaignTable campaigns={campaigns} />

        {/* Audit Alerts */}
        <AlertsFeed alerts={alerts} onAcknowledge={handleAcknowledge} />
      </div>
    </div>
  );
}
