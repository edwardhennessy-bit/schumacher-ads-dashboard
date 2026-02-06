"use client";

import { useState, useEffect, useCallback } from "react";
import { Header } from "@/components/layout/Header";
import { MetricCard } from "@/components/dashboard/MetricCard";
import {
  DollarSign,
  UserPlus,
  Users,
  TrendingUp,
  Facebook,
  Search,
  Monitor,
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
  formatDateRangeLabel,
} from "@/lib/date-range";

interface PlatformSummary {
  spend: number;
  spendChange: number;
  leads: number;
  leadsChange: number;
  cpl: number;
  cplChange: number;
  connected: boolean;
}

const emptyPlatform: PlatformSummary = {
  spend: 0,
  spendChange: 0,
  leads: 0,
  leadsChange: 0,
  cpl: 0,
  cplChange: 0,
  connected: false,
};

function toPlatform(m: MetricsOverview, connected: boolean): PlatformSummary {
  return {
    spend: m.spend,
    spendChange: m.spend_change,
    leads: m.leads,
    leadsChange: m.leads_change,
    cpl: m.cost_per_lead,
    cplChange: m.cost_per_lead_change,
    connected,
  };
}

export default function OverviewPage() {
  const [meta, setMeta] = useState<PlatformSummary>(emptyPlatform);
  const [google, setGoogle] = useState<PlatformSummary>(emptyPlatform);
  const [microsoft] = useState<PlatformSummary>(emptyPlatform); // placeholder
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

      if (metaRes.status === "fulfilled") {
        setMeta(toPlatform(metaRes.value, true));
      }
      if (googleRes.status === "fulfilled" && googleRes.value.spend > 0) {
        setGoogle(toPlatform(googleRes.value, true));
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
  const totalSpend = meta.spend + google.spend + microsoft.spend;
  const totalLeads = meta.leads + google.leads + microsoft.leads;
  const totalCpl = totalLeads > 0 ? totalSpend / totalLeads : 0;

  const platforms = [
    { name: "Meta", data: meta, icon: Facebook, color: "blue", href: "/meta" },
    { name: "Google", data: google, icon: Search, color: "green", href: "/google" },
    { name: "Microsoft", data: microsoft, icon: Monitor, color: "gray", href: "/microsoft" },
  ];

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

      <div className="p-6 space-y-6">
        {/* Aggregate Totals */}
        <div>
          <h2 className="text-lg font-semibold mb-3">All Platforms Combined</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
              value={formatCurrency(totalCpl)}
              icon={<Users className="h-4 w-4" />}
              className="border-2 border-green-200 bg-green-50/50"
            />
          </div>
        </div>

        {/* Per-Platform Breakdown */}
        <div>
          <h2 className="text-lg font-semibold mb-3">By Platform</h2>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {platforms.map((p) => {
              const colorMap: Record<string, string> = {
                blue: "border-blue-200 bg-blue-50/30",
                green: "border-green-200 bg-green-50/30",
                gray: "border-gray-200 bg-gray-50/30",
              };
              const headerColorMap: Record<string, string> = {
                blue: "text-blue-700",
                green: "text-green-700",
                gray: "text-gray-500",
              };
              const borderClass = colorMap[p.color] || "border-gray-200";
              const headerClass = headerColorMap[p.color] || "text-gray-700";

              return (
                <a
                  key={p.name}
                  href={p.href}
                  className={`rounded-xl border-2 p-5 transition-shadow hover:shadow-md ${borderClass}`}
                >
                  <div className="flex items-center gap-2 mb-4">
                    <p.icon className={`h-5 w-5 ${headerClass}`} />
                    <h3 className={`text-lg font-bold ${headerClass}`}>
                      {p.name}
                    </h3>
                    {!p.data.connected && p.name !== "Microsoft" && (
                      <span className="ml-auto text-xs px-2 py-0.5 rounded bg-yellow-100 text-yellow-700">
                        Not Connected
                      </span>
                    )}
                    {p.name === "Microsoft" && (
                      <span className="ml-auto text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-500">
                        Coming Soon
                      </span>
                    )}
                    {p.data.connected && (
                      <span className="ml-auto text-xs px-2 py-0.5 rounded bg-green-100 text-green-700">
                        Live
                      </span>
                    )}
                  </div>

                  <div className="space-y-3">
                    <div className="flex justify-between items-baseline">
                      <span className="text-sm text-muted-foreground">Spend</span>
                      <span className="text-lg font-semibold">
                        {formatCurrency(p.data.spend)}
                      </span>
                    </div>
                    <div className="flex justify-between items-baseline">
                      <span className="text-sm text-muted-foreground">Leads</span>
                      <span className="text-lg font-semibold">
                        {formatNumber(p.data.leads)}
                      </span>
                    </div>
                    <div className="flex justify-between items-baseline">
                      <span className="text-sm text-muted-foreground">CPL</span>
                      <span className="text-lg font-semibold">
                        {p.data.cpl > 0 ? formatCurrency(p.data.cpl) : "—"}
                      </span>
                    </div>
                  </div>

                  {p.data.connected && (
                    <div className="mt-4 pt-3 border-t text-xs text-muted-foreground flex items-center gap-1">
                      <TrendingUp className="h-3 w-3" />
                      {p.data.spendChange > 0 ? "+" : ""}{p.data.spendChange}% spend vs prior month
                    </div>
                  )}
                </a>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
