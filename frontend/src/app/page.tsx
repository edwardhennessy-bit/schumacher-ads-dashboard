"use client";

import { useState, useEffect, useCallback } from "react";
import { Header } from "@/components/layout/Header";
import { MetricCard } from "@/components/dashboard/MetricCard";
import {
  DollarSign,
  UserPlus,
  Users,
  Target,
  Monitor,
  RefreshCw,
  Megaphone,
} from "lucide-react";
import { formatCurrency, formatNumber } from "@/lib/mock-data";
import { api, MetricsOverview } from "@/lib/api";
import { BudgetTracker } from "@/components/dashboard/BudgetTracker";
import {
  DateRange,
  DEFAULT_PRESET,
  getPresetByValue,
} from "@/lib/date-range";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

interface MicrosoftData {
  connected: boolean;
  live: boolean;
  spend: number;
  spend_change: number;
  impressions: number;
  clicks: number;
  clicks_change: number;
  ctr: number;
  cpc: number;
  cpc_change: number;
  leads: number;
  leads_change: number;
  cost_per_lead: number;
  cost_per_lead_change: number;
  conversions: number;
  cost_per_conversion: number;
  campaigns: unknown[];
  start_date?: string;
  end_date?: string;
}

export default function OverviewPage() {
  const [metaData, setMetaData] = useState<MetricsOverview | null>(null);
  const [googleData, setGoogleData] = useState<MetricsOverview | null>(null);
  const [microsoftData, setMicrosoftData] = useState<MicrosoftData | null>(null);
  const [metaConnected, setMetaConnected] = useState<boolean | null>(null);
  const [googleConnected, setGoogleConnected] = useState<boolean | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const [selectedPreset, setSelectedPreset] = useState(DEFAULT_PRESET);
  const [customRange, setCustomRange] = useState<DateRange | null>(null);

  const getActiveDateRange = useCallback((): DateRange => {
    if (customRange) return customRange;
    const preset = getPresetByValue(selectedPreset);
    return preset ? preset.getRange() : getPresetByValue(DEFAULT_PRESET)!.getRange();
  }, [customRange, selectedPreset]);

  const fetchMicrosoftData = useCallback(async (dateRange: DateRange) => {
    try {
      const res = await fetch(
        `${API_BASE}/api/microsoft/overview?start_date=${dateRange.startDate}&end_date=${dateRange.endDate}`
      );
      if (res.ok) {
        const data: MicrosoftData = await res.json();
        if (data.connected) setMicrosoftData(data);
        else setMicrosoftData(null);
      }
    } catch (_) {
      // no stored data yet
    }
  }, []);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    const dateRange = getActiveDateRange();
    try {
      const [metaRes, googleRes] = await Promise.allSettled([
        api.getMetricsOverview(dateRange),
        api.getGoogleOverview(dateRange),
      ]);

      if (metaRes.status === "fulfilled") {
        setMetaData(metaRes.value);
        setMetaConnected(metaRes.value.spend > 0 || metaRes.value.impressions > 0);
      } else {
        setMetaConnected(false);
      }
      if (googleRes.status === "fulfilled") {
        setGoogleData(googleRes.value);
        setGoogleConnected(googleRes.value.spend > 0 || googleRes.value.impressions > 0);
      } else {
        setGoogleConnected(false);
      }

      await fetchMicrosoftData(dateRange);
    } catch (error) {
      console.log("Overview fetch error:", error);
    } finally {
      setIsLoading(false);
    }
  }, [getActiveDateRange, fetchMicrosoftData]);

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

  // Aggregate totals across all platforms
  const metaSpend = metaData?.spend ?? 0;
  const googleSpend = googleData?.spend ?? 0;
  const msSpend = microsoftData?.spend ?? 0;
  const totalSpend = metaSpend + googleSpend + msSpend;

  const metaLeads = metaData?.leads ?? 0;
  const googleLeads = googleData?.leads ?? 0;
  const msLeads = microsoftData?.leads ?? 0;
  const totalLeads = metaLeads + googleLeads + msLeads;

  const blendedCpl = totalLeads > 0 ? totalSpend / totalLeads : 0;

  const metaOpps = metaData?.opportunities ?? 0;
  const googleOpps = googleData?.opportunities ?? 0;
  const totalOpps = metaOpps + googleOpps;
  const blendedCpo = totalOpps > 0 ? totalSpend / totalOpps : 0;

  const msConnected = !!microsoftData?.connected;

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
        {/* ── All Platforms Combined ─────────────────────────────── */}
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
              className="border-2 border-[#f27038]/30 bg-[#f27038]/5"
            />
            <MetricCard
              title="Blended Cost / Opp"
              value={formatCurrency(blendedCpo)}
              invertTrend
              icon={<Users className="h-4 w-4" />}
              className="border-2 border-[#f27038]/30 bg-[#f27038]/5"
            />
          </div>
        </div>

        {/* ── Budget Tracker ────────────────────────────────────── */}
        <BudgetTracker
          startDate={getActiveDateRange().startDate}
          endDate={getActiveDateRange().endDate}
        />

        {/* ── Meta ──────────────────────────────────────────────── */}
        <div>
          <a href="/meta" className="group flex items-center gap-2 mb-3">
            <div className="w-3 h-3 rounded-full bg-[#f27038]" />
            <h2 className="text-lg font-semibold group-hover:underline">Meta</h2>
            {metaConnected === null ? (
              <span className="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-500">Loading...</span>
            ) : metaConnected ? (
              <span className="text-xs px-2 py-0.5 rounded bg-green-100 text-green-700">Live</span>
            ) : (
              <span className="text-xs px-2 py-0.5 rounded bg-yellow-100 text-yellow-700">Not Connected</span>
            )}
          </a>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            <MetricCard title="Spend" value={formatCurrency(metaSpend)}
              change={metaData?.spend_change} icon={<DollarSign className="h-4 w-4" />}
              className="border-l-4 border-l-[#f27038]" />
            <MetricCard title="Total Leads" value={formatNumber(metaLeads)}
              change={metaData?.leads_change} icon={<UserPlus className="h-4 w-4" />}
              className="border-l-4 border-l-[#f27038]" />
            <MetricCard title="Blended CPL" value={formatCurrency(metaData?.cost_per_lead ?? 0)}
              change={metaData?.cost_per_lead_change} invertTrend icon={<Users className="h-4 w-4" />}
              className="border-l-4 border-l-[#f27038]" />
            <MetricCard title="Remarketing CPL" value={formatCurrency(metaData?.remarketing_cpl ?? 0)}
              subtitle={`${formatNumber(metaData?.remarketing_leads ?? 0)} leads · ${formatCurrency(metaData?.remarketing_spend ?? 0)} spend`}
              icon={<RefreshCw className="h-4 w-4" />} className="border-l-4 border-l-[#f27038]" />
            <MetricCard title="Prospecting CPL" value={formatCurrency(metaData?.prospecting_cpl ?? 0)}
              subtitle={`${formatNumber(metaData?.prospecting_leads ?? 0)} leads · ${formatCurrency(metaData?.prospecting_spend ?? 0)} spend`}
              icon={<Megaphone className="h-4 w-4" />} className="border-l-4 border-l-[#f27038]" />
          </div>
        </div>

        {/* ── Google Ads ────────────────────────────────────────── */}
        <div>
          <a href="/google" className="group flex items-center gap-2 mb-3">
            <div className="w-3 h-3 rounded-full bg-green-500" />
            <h2 className="text-lg font-semibold group-hover:underline">Google Ads</h2>
            {googleConnected === null ? (
              <span className="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-500">Loading...</span>
            ) : googleConnected ? (
              <span className="text-xs px-2 py-0.5 rounded bg-green-100 text-green-700">Live</span>
            ) : (
              <span className="text-xs px-2 py-0.5 rounded bg-yellow-100 text-yellow-700">Not Connected</span>
            )}
          </a>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            <MetricCard title="Spend" value={formatCurrency(googleSpend)}
              change={googleData?.spend_change} icon={<DollarSign className="h-4 w-4" />}
              className="border-l-4 border-l-green-500" />
            <MetricCard title="MQLs (Leads)" value={formatNumber(googleLeads)}
              change={googleData?.leads_change} icon={<UserPlus className="h-4 w-4" />}
              className="border-l-4 border-l-green-500" />
            <MetricCard title="Cost / Lead" value={formatCurrency(googleData?.cost_per_lead ?? 0)}
              change={googleData?.cost_per_lead_change} invertTrend icon={<Users className="h-4 w-4" />}
              className="border-l-4 border-l-green-500" />
            <MetricCard title="Opportunities" value={formatNumber(googleOpps)}
              change={googleData?.opportunities_change} icon={<Target className="h-4 w-4" />}
              className="border-l-4 border-l-green-500" />
            <MetricCard title="Cost / Opportunity" value={formatCurrency(googleData?.cost_per_opportunity ?? 0)}
              change={googleData?.cost_per_opportunity_change} invertTrend icon={<Users className="h-4 w-4" />}
              className="border-l-4 border-l-green-500" />
          </div>
        </div>

        {/* ── Microsoft Ads ─────────────────────────────────────── */}
        <div>
          <a href="/microsoft" className="group flex items-center gap-2 mb-3">
            <div className={`w-3 h-3 rounded-full ${msConnected ? "bg-[#f27038]" : "bg-gray-400"}`} />
            <h2 className="text-lg font-semibold group-hover:underline">Microsoft Ads</h2>
            {msConnected ? (
              <span className="text-xs px-2 py-0.5 rounded bg-green-100 text-green-700">Live</span>
            ) : isLoading ? (
              <span className="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-500">Loading...</span>
            ) : (
              <span className="text-xs px-2 py-0.5 rounded bg-yellow-100 text-yellow-700">Not Connected</span>
            )}
          </a>

          <div className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 ${msConnected ? "" : "opacity-40"}`}>
            <MetricCard title="Spend"
              value={msConnected ? formatCurrency(msSpend) : "—"}
              change={microsoftData?.spend_change}
              icon={<Monitor className="h-4 w-4" />} className="border-l-4 border-l-[#f27038]" />
            <MetricCard title="Leads"
              value={msConnected ? formatNumber(msLeads) : "—"}
              change={microsoftData?.leads_change}
              icon={<UserPlus className="h-4 w-4" />} className="border-l-4 border-l-[#f27038]" />
            <MetricCard title="Cost / Lead"
              value={msConnected ? formatCurrency(microsoftData?.cost_per_lead ?? 0) : "—"}
              change={microsoftData?.cost_per_lead_change}
              invertTrend icon={<Users className="h-4 w-4" />} className="border-l-4 border-l-[#f27038]" />
            <MetricCard title="Clicks"
              value={msConnected ? formatNumber(microsoftData?.clicks ?? 0) : "—"}
              change={microsoftData?.clicks_change}
              icon={<Target className="h-4 w-4" />} className="border-l-4 border-l-[#f27038]" />
            <MetricCard title="Avg. CPC"
              value={msConnected ? formatCurrency(microsoftData?.cpc ?? 0) : "—"}
              change={microsoftData?.cpc_change}
              invertTrend icon={<DollarSign className="h-4 w-4" />} className="border-l-4 border-l-[#f27038]" />
          </div>
        </div>
      </div>
    </div>
  );
}
