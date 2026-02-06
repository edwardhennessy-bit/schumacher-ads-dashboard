"use client";

import { useState, useEffect, useCallback } from "react";
import { Header } from "@/components/layout/Header";
import { MetricCard } from "@/components/dashboard/MetricCard";
import { TrendChart } from "@/components/dashboard/TrendChart";
import { CampaignTable } from "@/components/dashboard/CampaignTable";
import {
  DollarSign,
  MousePointer,
  Eye,
  Target,
  TrendingUp,
  Users,
  UserPlus,
  Search,
} from "lucide-react";
import {
  formatCurrency,
  formatNumber,
  formatPercent,
} from "@/lib/mock-data";
import { api, MetricsOverview, DailyMetric, Campaign } from "@/lib/api";
import {
  DateRange,
  DEFAULT_PRESET,
  getPresetByValue,
  formatDateRangeLabel,
} from "@/lib/date-range";

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
    leads: apiMetrics.leads,
    leadsChange: apiMetrics.leads_change,
    costPerLead: apiMetrics.cost_per_lead,
    costPerLeadChange: apiMetrics.cost_per_lead_change,
    conversions: apiMetrics.conversions,
    conversionsChange: apiMetrics.conversions_change,
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
    objective: c.objective || "",
    spend: c.spend,
    impressions: c.impressions,
    clicks: c.clicks,
    ctr: c.ctr,
    cpc: c.cpc,
    conversions: c.conversions,
    costPerConversion: c.cost_per_conversion,
    leads: c.leads,
    costPerLead: c.cost_per_lead,
    leadRate: c.lead_rate,
  };
}

const emptyMetrics = {
  spend: 0,
  spendChange: 0,
  impressions: 0,
  impressionsChange: 0,
  clicks: 0,
  clicksChange: 0,
  ctr: 0,
  ctrChange: 0,
  cpc: 0,
  cpcChange: 0,
  leads: 0,
  leadsChange: 0,
  costPerLead: 0,
  costPerLeadChange: 0,
  conversions: 0,
  conversionsChange: 0,
};

export default function GoogleDashboardPage() {
  const [metrics, setMetrics] = useState(emptyMetrics);
  const [trends, setTrends] = useState<any[]>([]);
  const [campaigns, setCampaigns] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [googleConnected, setGoogleConnected] = useState(false);

  const [selectedPreset, setSelectedPreset] = useState(DEFAULT_PRESET);
  const [customRange, setCustomRange] = useState<DateRange | null>(null);

  const getActiveDateRange = useCallback((): DateRange => {
    if (customRange) return customRange;
    const preset = getPresetByValue(selectedPreset);
    return preset ? preset.getRange() : getPresetByValue(DEFAULT_PRESET)!.getRange();
  }, [customRange, selectedPreset]);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    const dateRange = getActiveDateRange();
    try {
      const [metricsRes, trendsRes, campaignsRes] = await Promise.all([
        api.getGoogleOverview(dateRange),
        api.getGoogleTrends(365, dateRange),
        api.getGoogleCampaigns(dateRange),
      ]);

      setMetrics(transformMetrics(metricsRes));
      setTrends(trendsRes.map(transformTrend));
      setCampaigns(campaignsRes.map(transformCampaign));
      setGoogleConnected(true);
    } catch (error) {
      console.log("Google API not available:", error);
      setGoogleConnected(false);
    } finally {
      setIsLoading(false);
    }
  }, [getActiveDateRange]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handlePresetChange = (preset: string) => {
    setSelectedPreset(preset);
    setCustomRange(null);
  };

  const handleCustomRangeChange = (range: DateRange) => {
    setCustomRange(range);
  };

  const chartTitle = `${formatDateRangeLabel(selectedPreset, customRange)} Performance Trends`;

  return (
    <div className="min-h-screen bg-background">
      <Header
        title="Google Ads"
        subtitle={`Google Ads Performance Overview${!googleConnected ? " (Not Connected)" : ""}`}
        onRefresh={fetchData}
        isLoading={isLoading}
        selectedPreset={selectedPreset}
        customRange={customRange}
        onPresetChange={handlePresetChange}
        onCustomRangeChange={handleCustomRangeChange}
      />

      <div className="p-6 space-y-6">
        {!googleConnected && (
          <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4">
            <div className="flex items-center gap-2">
              <Search className="h-5 w-5 text-yellow-600" />
              <h3 className="font-semibold text-yellow-800">Google Ads Not Connected</h3>
            </div>
            <p className="mt-1 text-sm text-yellow-700">
              Add Google Ads API credentials to the backend .env file to enable live data.
              Required: GOOGLE_ADS_DEVELOPER_TOKEN, GOOGLE_ADS_CLIENT_ID,
              GOOGLE_ADS_CLIENT_SECRET, GOOGLE_ADS_REFRESH_TOKEN.
            </p>
          </div>
        )}

        {/* Lead Metrics Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
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
            icon={<Users className="h-4 w-4" />}
            className="border-2 border-green-200 bg-green-50/50"
          />
          <MetricCard
            title="Total Spend"
            value={formatCurrency(metrics.spend)}
            change={metrics.spendChange}
            icon={<DollarSign className="h-4 w-4" />}
            className="border-2 border-blue-200 bg-blue-50/50"
          />
          <MetricCard
            title="Conversions"
            value={formatNumber(metrics.conversions)}
            change={metrics.conversionsChange}
            icon={<Target className="h-4 w-4" />}
            className="border-2 border-purple-200 bg-purple-50/50"
          />
        </div>

        {/* Standard Metric Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
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
            icon={<Target className="h-4 w-4" />}
          />
        </div>

        {/* Trend Chart */}
        {trends.length > 0 && (
          <TrendChart data={trends} title={chartTitle} />
        )}

        {/* Campaign Table */}
        {campaigns.length > 0 && (
          <CampaignTable campaigns={campaigns} />
        )}
      </div>
    </div>
  );
}
