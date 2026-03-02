"use client";

import { useState, useEffect, useCallback } from "react";
import { Header } from "@/components/layout/Header";
import { MetricCard } from "@/components/dashboard/MetricCard";
import {
  Monitor,
  DollarSign,
  UserPlus,
  Users,
  MousePointerClick,
  Target,
} from "lucide-react";
import { formatCurrency, formatNumber } from "@/lib/mock-data";
import { DateRange, DEFAULT_PRESET, getPresetByValue } from "@/lib/date-range";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

interface Campaign {
  id: string;
  name: string;
  status: string;
  spend: number;
  impressions: number;
  clicks: number;
  ctr: number;
  cpc: number;
  conversions: number;
  cost_per_conversion: number;
}

interface MicrosoftData {
  connected: boolean;
  live: boolean;
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
  leads: number;
  leads_change: number;
  cost_per_lead: number;
  cost_per_lead_change: number;
  conversions: number;
  conversions_change: number;
  cost_per_conversion: number;
  campaigns: Campaign[];
  start_date?: string;
  end_date?: string;
}

export default function MicrosoftDashboardPage() {
  const [data, setData] = useState<MicrosoftData | null>(null);
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
    const dr = getActiveDateRange();
    try {
      const res = await fetch(
        `${API_BASE}/api/microsoft/overview?start_date=${dr.startDate}&end_date=${dr.endDate}`
      );
      if (res.ok) {
        const d: MicrosoftData = await res.json();
        setData(d.connected ? d : null);
      }
    } catch (err) {
      console.error("Microsoft fetch error:", err);
      setData(null);
    } finally {
      setIsLoading(false);
    }
  }, [getActiveDateRange]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const connected = !!data?.connected;

  return (
    <div className="min-h-screen bg-background">
      <Header
        title="Microsoft Ads"
        subtitle="Microsoft Advertising Performance"
        onRefresh={fetchData}
        isLoading={isLoading}
        selectedPreset={selectedPreset}
        customRange={customRange}
        onPresetChange={(p) => { setSelectedPreset(p); setCustomRange(null); }}
        onCustomRangeChange={setCustomRange}
      />

      <div className="p-6 space-y-6">
        {/* Status badge */}
        <div className="flex items-center gap-3">
          <div className={`w-3 h-3 rounded-full ${connected ? "bg-cyan-500" : "bg-gray-400"}`} />
          {connected ? (
            <span className="flex items-center gap-1.5 text-xs px-2 py-0.5 rounded bg-green-100 text-green-700 font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
              Live
            </span>
          ) : (
            <span className="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-500">Not Connected</span>
          )}
          {data?.start_date && data?.end_date && (
            <span className="text-xs text-gray-400">
              {data.start_date} → {data.end_date}
            </span>
          )}
        </div>

        {connected && data ? (
          <>
            {/* Primary KPIs */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
              <MetricCard
                title="Spend"
                value={formatCurrency(data.spend)}
                change={data.spend_change}
                icon={<DollarSign className="h-4 w-4" />}
                className="border-l-4 border-l-cyan-500"
              />
              <MetricCard
                title="Leads / Conversions"
                value={formatNumber(data.leads)}
                change={data.leads_change}
                icon={<UserPlus className="h-4 w-4" />}
                className="border-l-4 border-l-cyan-500"
              />
              <MetricCard
                title="Cost / Lead"
                value={formatCurrency(data.cost_per_lead)}
                change={data.cost_per_lead_change}
                invertTrend
                icon={<Users className="h-4 w-4" />}
                className="border-l-4 border-l-cyan-500"
              />
              <MetricCard
                title="Clicks"
                value={formatNumber(data.clicks)}
                change={data.clicks_change}
                icon={<MousePointerClick className="h-4 w-4" />}
                className="border-l-4 border-l-cyan-500"
              />
              <MetricCard
                title="Avg. CPC"
                value={formatCurrency(data.cpc)}
                change={data.cpc_change}
                invertTrend
                icon={<DollarSign className="h-4 w-4" />}
                className="border-l-4 border-l-cyan-500"
              />
            </div>

            {/* Secondary KPIs */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <MetricCard
                title="Impressions"
                value={formatNumber(data.impressions)}
                change={data.impressions_change}
                icon={<Monitor className="h-4 w-4" />}
                className="border-l-4 border-l-cyan-500"
              />
              <MetricCard
                title="CTR"
                value={`${data.ctr.toFixed(2)}%`}
                change={data.ctr_change}
                icon={<MousePointerClick className="h-4 w-4" />}
                className="border-l-4 border-l-cyan-500"
              />
              <MetricCard
                title="Conversions"
                value={formatNumber(data.conversions)}
                change={data.conversions_change}
                icon={<Target className="h-4 w-4" />}
                className="border-l-4 border-l-cyan-500"
              />
            </div>

            {/* Campaign breakdown */}
            {data.campaigns && data.campaigns.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold mb-3 text-gray-700">
                  Campaign Breakdown ({data.campaigns.length} campaigns)
                </h3>
                <div className="rounded-lg border overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
                      <tr>
                        <th className="px-4 py-2 text-left">Campaign</th>
                        <th className="px-4 py-2 text-right">Spend</th>
                        <th className="px-4 py-2 text-right">Clicks</th>
                        <th className="px-4 py-2 text-right">Impressions</th>
                        <th className="px-4 py-2 text-right">Conv.</th>
                        <th className="px-4 py-2 text-right">CPL</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {data.campaigns.map((c) => (
                        <tr key={c.id} className="hover:bg-gray-50">
                          <td className="px-4 py-2 font-medium text-gray-800 max-w-xs truncate">
                            {c.name || "—"}
                          </td>
                          <td className="px-4 py-2 text-right text-gray-600">
                            {formatCurrency(c.spend)}
                          </td>
                          <td className="px-4 py-2 text-right text-gray-600">
                            {formatNumber(c.clicks)}
                          </td>
                          <td className="px-4 py-2 text-right text-gray-600">
                            {formatNumber(c.impressions)}
                          </td>
                          <td className="px-4 py-2 text-right text-gray-600">
                            {c.conversions}
                          </td>
                          <td className="px-4 py-2 text-right text-gray-600">
                            {c.cost_per_conversion > 0 ? formatCurrency(c.cost_per_conversion) : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="flex flex-col items-center justify-center py-20">
            <div className="rounded-full bg-cyan-50 p-6 mb-6">
              <Monitor className="h-12 w-12 text-cyan-500" />
            </div>
            <h2 className="text-xl font-bold mb-2">
              {isLoading ? "Loading Microsoft Ads data..." : "No data available"}
            </h2>
            <p className="text-muted-foreground text-center max-w-md">
              {isLoading
                ? "Fetching live data from Microsoft Ads via the gateway..."
                : "No Microsoft Ads data was returned for the selected date range."}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
