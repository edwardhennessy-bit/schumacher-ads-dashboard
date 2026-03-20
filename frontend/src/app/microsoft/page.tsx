"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { Header } from "@/components/layout/Header";
import { MetricCard } from "@/components/dashboard/MetricCard";
import { ActiveAdsTree } from "@/components/dashboard/ActiveAdsTree";
import { JarvisProvider } from "@/context/JarvisContext";
import {
  JarvisDrawer,
  AskJarvisButton,
} from "@/components/dashboard/JarvisDrawer";
import {
  Monitor,
  DollarSign,
  UserPlus,
  Users,
  MousePointerClick,
  Target,
  ChevronUp,
  ChevronDown,
  ChevronsUpDown,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { formatCurrency, formatNumber } from "@/lib/mock-data";
import { api, ActiveAdsTree as ActiveAdsTreeData } from "@/lib/api";
import { DateRange, DEFAULT_PRESET, getPresetByValue } from "@/lib/date-range";

type SortColumn = "name" | "spend" | "clicks" | "impressions" | "conversions" | "cost_per_conversion";
type SortDir = "asc" | "desc";

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

const PAGE_SIZE_OPTIONS = [10, 25, 50];

function SortIcon({ column, sortColumn, sortDir }: { column: SortColumn; sortColumn: SortColumn; sortDir: SortDir }) {
  if (sortColumn !== column) return <ChevronsUpDown className="h-3 w-3 ml-1 text-gray-400 inline" />;
  return sortDir === "desc"
    ? <ChevronDown className="h-3 w-3 ml-1 text-[#f27038] inline" />
    : <ChevronUp className="h-3 w-3 ml-1 text-[#f27038] inline" />;
}

export default function MicrosoftDashboardPage() {
  const [data, setData] = useState<MicrosoftData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedPreset, setSelectedPreset] = useState(DEFAULT_PRESET);
  const [customRange, setCustomRange] = useState<DateRange | null>(null);

  // Campaign table state
  const [sortColumn, setSortColumn] = useState<SortColumn>("spend");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [filterActive, setFilterActive] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Active Ads Tree state
  const [adsTreeData, setAdsTreeData] = useState<ActiveAdsTreeData | null>(null);
  const [adsTreeLoading, setAdsTreeLoading] = useState(false);
  const [adsTreeStartDate, setAdsTreeStartDate] = useState<string>(() => {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10);
  });
  const [adsTreeEndDate, setAdsTreeEndDate] = useState<string>(() => new Date().toISOString().slice(0, 10));

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

  // Auto-load active ads tree on mount
  useEffect(() => {
    handleActiveAdsTreeOpen(adsTreeStartDate, adsTreeEndDate, "active");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const connected = !!data?.connected;

  // Derived campaign table data
  const handleSort = (col: SortColumn) => {
    if (sortColumn === col) {
      setSortDir(d => d === "desc" ? "asc" : "desc");
    } else {
      setSortColumn(col);
      setSortDir("desc");
    }
    setCurrentPage(1);
  };

  const filteredSortedCampaigns = useMemo(() => {
    const campaigns = data?.campaigns ?? [];
    const filtered = filterActive
      ? campaigns.filter(c => c.status?.toLowerCase() === "active")
      : campaigns;
    return [...filtered].sort((a, b) => {
      const aVal = a[sortColumn] ?? 0;
      const bVal = b[sortColumn] ?? 0;
      if (typeof aVal === "string" && typeof bVal === "string") {
        return sortDir === "desc" ? bVal.localeCompare(aVal) : aVal.localeCompare(bVal);
      }
      return sortDir === "desc" ? (bVal as number) - (aVal as number) : (aVal as number) - (bVal as number);
    });
  }, [data?.campaigns, filterActive, sortColumn, sortDir]);

  const totalPages = Math.max(1, Math.ceil(filteredSortedCampaigns.length / pageSize));
  const pagedCampaigns = filteredSortedCampaigns.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  const handleActiveAdsTreeOpen = async (startDate: string, endDate: string, mode: "active" | "with_spend" = "active") => {
    setAdsTreeLoading(true);
    setAdsTreeStartDate(startDate);
    setAdsTreeEndDate(endDate);
    try {
      const result = await api.getMicrosoftActiveAdsTree(startDate, endDate, mode);
      setAdsTreeData(result);
    } catch (err) {
      console.error("Microsoft active ads tree error:", err);
    } finally {
      setAdsTreeLoading(false);
    }
  };

  return (
    <JarvisProvider>
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
          <div className={`w-3 h-3 rounded-full ${connected ? "bg-[#f27038]" : "bg-gray-400"}`} />
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
            <div id="kpi_cards">
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-sm font-semibold text-gray-700">Key Metrics</h2>
              <AskJarvisButton section="kpi_cards" />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
              <MetricCard
                title="Spend"
                value={formatCurrency(data.spend)}
                change={data.spend_change}
                icon={<DollarSign className="h-4 w-4" />}
                className="border-l-4 border-l-[#f27038]"
              />
              <MetricCard
                title="Leads / Conversions"
                value={formatNumber(data.leads)}
                change={data.leads_change}
                icon={<UserPlus className="h-4 w-4" />}
                className="border-l-4 border-l-[#f27038]"
              />
              <MetricCard
                title="Cost / Lead"
                value={formatCurrency(data.cost_per_lead)}
                change={data.cost_per_lead_change}
                invertTrend
                icon={<Users className="h-4 w-4" />}
                className="border-l-4 border-l-[#f27038]"
              />
              <MetricCard
                title="Clicks"
                value={formatNumber(data.clicks)}
                change={data.clicks_change}
                icon={<MousePointerClick className="h-4 w-4" />}
                className="border-l-4 border-l-[#f27038]"
              />
              <MetricCard
                title="Avg. CPC"
                value={formatCurrency(data.cpc)}
                change={data.cpc_change}
                invertTrend
                icon={<DollarSign className="h-4 w-4" />}
                className="border-l-4 border-l-[#f27038]"
              />
            </div>

            {/* Secondary KPIs */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <MetricCard
                title="Impressions"
                value={formatNumber(data.impressions)}
                change={data.impressions_change}
                icon={<Monitor className="h-4 w-4" />}
                className="border-l-4 border-l-[#f27038]"
              />
              <MetricCard
                title="CTR"
                value={`${data.ctr.toFixed(2)}%`}
                change={data.ctr_change}
                icon={<MousePointerClick className="h-4 w-4" />}
                className="border-l-4 border-l-[#f27038]"
              />
              <MetricCard
                title="Conversions"
                value={formatNumber(data.conversions)}
                change={data.conversions_change}
                icon={<Target className="h-4 w-4" />}
                className="border-l-4 border-l-[#f27038]"
              />
            </div>
            </div>{/* end kpi_cards */}

            {/* Active Ads Section */}
            <div id="active_ads">
              <div className="flex items-center justify-between mb-2">
                <h2 className="text-sm font-semibold text-gray-700">Microsoft Active Ads</h2>
                <AskJarvisButton section="active_ads" />
              </div>
              <ActiveAdsTree
                platform="microsoft"
                totalActiveAds={adsTreeData?.total_active_ads ?? 0}
                campaigns={adsTreeData?.campaigns ?? []}
                isLoading={adsTreeLoading}
                onOpen={handleActiveAdsTreeOpen}
                startDate={adsTreeStartDate}
                endDate={adsTreeEndDate}
                onDateChange={(s, e) => { setAdsTreeStartDate(s); setAdsTreeEndDate(e); }}
              />
            </div>

            {/* Campaign breakdown */}
            {data.campaigns && data.campaigns.length > 0 && (
              <div id="campaign_table">
                <div className="flex items-center justify-between mb-2">
                  <h2 className="text-sm font-semibold text-gray-700">Campaign Breakdown</h2>
                  <AskJarvisButton section="campaign_table" />
                </div>

                {/* Toolbar */}
                <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
                  <div className="flex items-center gap-4">
                    <span className="text-xs text-gray-500">
                      {filteredSortedCampaigns.length} of {data.campaigns.length} campaigns
                    </span>
                    <label className="flex items-center gap-1.5 cursor-pointer select-none">
                      <input
                        type="checkbox"
                        checked={filterActive}
                        onChange={e => { setFilterActive(e.target.checked); setCurrentPage(1); }}
                        className="rounded border-gray-300 text-[#f27038] focus:ring-[#f27038]"
                      />
                      <span className="text-xs text-gray-600 font-medium">Active only</span>
                    </label>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-gray-500">
                    <span>Rows per page:</span>
                    <select
                      value={pageSize}
                      onChange={e => { setPageSize(Number(e.target.value)); setCurrentPage(1); }}
                      className="border border-gray-200 rounded px-2 py-0.5 text-xs text-gray-700 focus:outline-none focus:ring-1 focus:ring-[#f27038]"
                    >
                      {PAGE_SIZE_OPTIONS.map(n => (
                        <option key={n} value={n}>{n}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="rounded-lg border overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
                      <tr>
                        {(
                          [
                            { col: "name" as SortColumn, label: "Campaign", align: "left" },
                            { col: "spend" as SortColumn, label: "Spend", align: "right" },
                            { col: "clicks" as SortColumn, label: "Clicks", align: "right" },
                            { col: "impressions" as SortColumn, label: "Impressions", align: "right" },
                            { col: "conversions" as SortColumn, label: "Conv.", align: "right" },
                            { col: "cost_per_conversion" as SortColumn, label: "CPL", align: "right" },
                          ] as { col: SortColumn; label: string; align: string }[]
                        ).map(({ col, label, align }) => (
                          <th
                            key={col}
                            className={`px-4 py-2 text-${align} cursor-pointer select-none hover:bg-gray-100 transition-colors`}
                            onClick={() => handleSort(col)}
                          >
                            <span className="inline-flex items-center gap-0.5">
                              {label}
                              <SortIcon column={col} sortColumn={sortColumn} sortDir={sortDir} />
                            </span>
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {pagedCampaigns.length === 0 ? (
                        <tr>
                          <td colSpan={6} className="px-4 py-8 text-center text-gray-400 text-xs">
                            No campaigns match the current filter.
                          </td>
                        </tr>
                      ) : pagedCampaigns.map((c, idx) => (
                        <tr key={`${c.id}-${idx}`} className="hover:bg-gray-50">
                          <td className="px-4 py-2 font-medium text-gray-800 max-w-xs truncate">
                            <span title={c.name || ""}>{c.name || "—"}</span>
                            {c.status && (
                              <span className={`ml-2 text-xs px-1.5 py-0.5 rounded font-normal ${
                                c.status.toLowerCase() === "active"
                                  ? "bg-green-100 text-green-700"
                                  : "bg-gray-100 text-gray-500"
                              }`}>
                                {c.status}
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-2 text-right text-gray-600 tabular-nums">
                            {formatCurrency(c.spend)}
                          </td>
                          <td className="px-4 py-2 text-right text-gray-600 tabular-nums">
                            {formatNumber(c.clicks)}
                          </td>
                          <td className="px-4 py-2 text-right text-gray-600 tabular-nums">
                            {formatNumber(c.impressions)}
                          </td>
                          <td className="px-4 py-2 text-right text-gray-600 tabular-nums">
                            {c.conversions}
                          </td>
                          <td className="px-4 py-2 text-right text-gray-600 tabular-nums">
                            {c.cost_per_conversion > 0 ? formatCurrency(c.cost_per_conversion) : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-between mt-3 px-1">
                    <span className="text-xs text-gray-500">
                      Page {currentPage} of {totalPages}
                    </span>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                        disabled={currentPage === 1}
                        className="p-1.5 rounded border border-gray-200 text-gray-500 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                      >
                        <ChevronLeft className="h-3.5 w-3.5" />
                      </button>
                      {Array.from({ length: totalPages }, (_, i) => i + 1)
                        .filter(p => p === 1 || p === totalPages || Math.abs(p - currentPage) <= 1)
                        .reduce<(number | "...")[]>((acc, p, idx, arr) => {
                          if (idx > 0 && (arr[idx - 1] as number) + 1 < p) acc.push("...");
                          acc.push(p);
                          return acc;
                        }, [])
                        .map((p, idx) =>
                          p === "..." ? (
                            <span key={`ellipsis-${idx}`} className="px-1.5 text-xs text-gray-400">…</span>
                          ) : (
                            <button
                              key={p}
                              onClick={() => setCurrentPage(p as number)}
                              className={`min-w-[28px] h-7 rounded border text-xs font-medium transition-colors ${
                                currentPage === p
                                  ? "border-[#f27038] bg-[#f27038] text-white"
                                  : "border-gray-200 text-gray-600 hover:bg-gray-50"
                              }`}
                            >
                              {p}
                            </button>
                          )
                        )}
                      <button
                        onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                        disabled={currentPage === totalPages}
                        className="p-1.5 rounded border border-gray-200 text-gray-500 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                      >
                        <ChevronRight className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </>
        ) : (
          <div className="flex flex-col items-center justify-center py-20">
            <div className="rounded-full bg-[#f27038]/10 p-6 mb-6">
              <Monitor className="h-12 w-12 text-[#f27038]" />
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
    <JarvisDrawer />
    </JarvisProvider>
  );
}
