"use client";

import { useState, useEffect, useCallback } from "react";
import { Header } from "@/components/layout/Header";
import { MetricCard } from "@/components/dashboard/MetricCard";
import {
  DollarSign,
  UserPlus,
  Users,
  Target,
  Search,
  Monitor,
  RefreshCw,
  Megaphone,
} from "lucide-react";
import {
  formatCurrency,
  formatNumber,
} from "@/lib/mock-data";
import { api, MetricsOverview } from "@/lib/api";
import {
  DateRange,
  DEFAULT_PRESET,
  getPresetByValue,
} from "@/lib/date-range";

export default function OverviewPage() {
  const [metaData, setMetaData] = useState<MetricsOverview | null>(null);
  const [googleData, setGoogleData] = useState<MetricsOverview | null>(null);
  const [isLoading, setIsLoading] = useState(false);

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
      const [metaRes, googleRes] = await Promise.allSettled([
        api.getMetricsOverview(dateRange),
        api.getGoogleOverview(dateRange),
      ]);

      if (metaRes.status === "fulfilled" && metaRes.value.spend > 0) {
        setMetaData(metaRes.value);
      }
      if (googleRes.status === "fulfilled" && googleRes.value.spend > 0) {
        setGoogleData(googleRes.value);
      }
    } catch (error) {
      console.log("Overview fetch error:", error);
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

  // Aggregate totals
  const metaSpend = metaData?.spend ?? 0;
  const googleSpend = googleData?.spend ?? 0;
  const totalSpend = metaSpend + googleSpend;

  const metaLeads = metaData?.leads ?? 0;
  const googleLeads = googleData?.leads ?? 0;
  const totalLeads = metaLeads + googleLeads;

  const blendedCpl = totalLeads > 0 ? totalSpend / totalLeads : 0;

  const metaOpps = metaData?.opportunities ?? 0;
  const googleOpps = googleData?.opportunities ?? 0;
  const totalOpps = metaOpps + googleOpps;

  const blendedCpo = totalOpps > 0 ? totalSpend / totalOpps : 0;

  return (
    <div className="min-h-screen bg-background">
      <Header
        title="Overview"
        subtitle="Cross-Platform Performance Summary"
        onRefresh={fetchData}
        isLoading={isLoading}
        selectedPreset={selectedPreset}
        customRange={customRange}
        onPresetChange={handlePresetChange}
        onCustomRangeChange={handleCustomRangeChange}
      />

      <div className="p-6 space-y-8">
        {/* ── All Platforms Combined ────────────────────────────────── */}
        <div>
          <h2 className="text-lg font-semibold mb-3">All Platforms</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            <MetricCard
              title="Total Spend"
              value={formatCurrency(totalSpend)}
              icon={<DollarSign className="h-4 w-4" />}
              className="border-2 border-gray-200"
            />
            <MetricCard
              title="Total Leads"
              value={formatNumber(totalLeads)}
              icon={<UserPlus className="h-4 w-4" />}
              className="border-2 border-green-200 bg-green-50/50"
            />
            <MetricCard
              title="Blended CPL"
              value={formatCurrency(blendedCpl)}
              invertTrend
              icon={<Users className="h-4 w-4" />}
              className="border-2 border-green-200 bg-green-50/50"
            />
            <MetricCard
              title="Total Opportunities"
              value={formatNumber(totalOpps)}
              icon={<Target className="h-4 w-4" />}
              className="border-2 border-purple-200 bg-purple-50/50"
            />
            <MetricCard
              title="Blended Cost / Opp"
              value={formatCurrency(blendedCpo)}
              invertTrend
              icon={<Users className="h-4 w-4" />}
              className="border-2 border-purple-200 bg-purple-50/50"
            />
          </div>
        </div>

        {/* ── Meta (Facebook / Instagram) ──────────────────────────── */}
        <div>
          <a href="/meta" className="group flex items-center gap-2 mb-3">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-blue-500" />
              <h2 className="text-lg font-semibold group-hover:underline">Meta</h2>
            </div>
            {metaData ? (
              <span className="text-xs px-2 py-0.5 rounded bg-green-100 text-green-700">Live</span>
            ) : (
              <span className="text-xs px-2 py-0.5 rounded bg-yellow-100 text-yellow-700">Not Connected</span>
            )}
          </a>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            <MetricCard
              title="Spend"
              value={formatCurrency(metaSpend)}
              change={metaData?.spend_change}
              icon={<DollarSign className="h-4 w-4" />}
              className="border-l-4 border-l-blue-500"
            />
            <MetricCard
              title="Total Leads"
              value={formatNumber(metaLeads)}
              change={metaData?.leads_change}
              icon={<UserPlus className="h-4 w-4" />}
              className="border-l-4 border-l-blue-500"
            />
            <MetricCard
              title="Blended CPL"
              value={formatCurrency(metaData?.cost_per_lead ?? 0)}
              change={metaData?.cost_per_lead_change}
              invertTrend
              icon={<Users className="h-4 w-4" />}
              className="border-l-4 border-l-blue-500"
            />
            <MetricCard
              title="Remarketing CPL"
              value={formatCurrency(metaData?.remarketing_cpl ?? 0)}
              subtitle={`${formatNumber(metaData?.remarketing_leads ?? 0)} leads · ${formatCurrency(metaData?.remarketing_spend ?? 0)} spend`}
              icon={<RefreshCw className="h-4 w-4" />}
              className="border-l-4 border-l-blue-500"
            />
            <MetricCard
              title="Prospecting CPL"
              value={formatCurrency(metaData?.prospecting_cpl ?? 0)}
              subtitle={`${formatNumber(metaData?.prospecting_leads ?? 0)} leads · ${formatCurrency(metaData?.prospecting_spend ?? 0)} spend`}
              icon={<Megaphone className="h-4 w-4" />}
              className="border-l-4 border-l-blue-500"
            />
          </div>
        </div>

        {/* ── Google Ads ───────────────────────────────────────────── */}
        <div>
          <a href="/google" className="group flex items-center gap-2 mb-3">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-green-500" />
              <h2 className="text-lg font-semibold group-hover:underline">Google Ads</h2>
            </div>
            {googleData ? (
              <span className="text-xs px-2 py-0.5 rounded bg-green-100 text-green-700">Live</span>
            ) : (
              <span className="text-xs px-2 py-0.5 rounded bg-yellow-100 text-yellow-700">Not Connected</span>
            )}
          </a>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            <MetricCard
              title="Spend"
              value={formatCurrency(googleSpend)}
              change={googleData?.spend_change}
              icon={<DollarSign className="h-4 w-4" />}
              className="border-l-4 border-l-green-500"
            />
            <MetricCard
              title="MQLs (Leads)"
              value={formatNumber(googleLeads)}
              change={googleData?.leads_change}
              icon={<UserPlus className="h-4 w-4" />}
              className="border-l-4 border-l-green-500"
            />
            <MetricCard
              title="Cost / Lead"
              value={formatCurrency(googleData?.cost_per_lead ?? 0)}
              change={googleData?.cost_per_lead_change}
              invertTrend
              icon={<Users className="h-4 w-4" />}
              className="border-l-4 border-l-green-500"
            />
            <MetricCard
              title="Opportunities"
              value={formatNumber(googleOpps)}
              change={googleData?.opportunities_change}
              icon={<Target className="h-4 w-4" />}
              className="border-l-4 border-l-green-500"
            />
            <MetricCard
              title="Cost / Opportunity"
              value={formatCurrency(googleData?.cost_per_opportunity ?? 0)}
              change={googleData?.cost_per_opportunity_change}
              invertTrend
              icon={<Users className="h-4 w-4" />}
              className="border-l-4 border-l-green-500"
            />
          </div>
        </div>

        {/* ── Microsoft Ads (Coming Soon) ──────────────────────────── */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <div className="w-3 h-3 rounded-full bg-gray-400" />
            <h2 className="text-lg font-semibold text-gray-400">Microsoft Ads</h2>
            <span className="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-500">Coming Soon</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 opacity-40">
            <MetricCard
              title="Spend"
              value="—"
              icon={<Monitor className="h-4 w-4" />}
              className="border-l-4 border-l-gray-300"
            />
            <MetricCard
              title="Leads"
              value="—"
              icon={<UserPlus className="h-4 w-4" />}
              className="border-l-4 border-l-gray-300"
            />
            <MetricCard
              title="CPL"
              value="—"
              icon={<Users className="h-4 w-4" />}
              className="border-l-4 border-l-gray-300"
            />
            <MetricCard
              title="Opportunities"
              value="—"
              icon={<Target className="h-4 w-4" />}
              className="border-l-4 border-l-gray-300"
            />
            <MetricCard
              title="Cost / Opportunity"
              value="—"
              icon={<Users className="h-4 w-4" />}
              className="border-l-4 border-l-gray-300"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
