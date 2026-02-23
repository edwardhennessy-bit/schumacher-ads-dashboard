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
  ScanSearch,
  CheckCircle2,
  Clock,
  Target,
} from "lucide-react";
import { formatCurrency, formatNumber } from "@/lib/mock-data";
import { DateRange, DEFAULT_PRESET, getPresetByValue } from "@/lib/date-range";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

interface MicrosoftData {
  connected: boolean;
  spend: number;
  impressions: number;
  clicks: number;
  ctr: number;
  cpc: number;
  leads: number;
  cost_per_lead: number;
  conversions: number;
  cost_per_conversion: number;
  campaigns: Array<{ name: string; spend: string; clicks: string; impressions: string }>;
  start_date?: string;
  end_date?: string;
  scraped_at?: string;
}

export default function MicrosoftDashboardPage() {
  const [data, setData] = useState<MicrosoftData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isScraping, setIsScraping] = useState(false);
  const [scrapeStatus, setScrapeStatus] = useState("");
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
    } finally {
      setIsLoading(false);
    }
  }, [getActiveDateRange]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleScrape = async () => {
    if (isScraping) return;
    setIsScraping(true);
    setScrapeStatus("Opening Microsoft Ads...");

    const dateRange = getActiveDateRange();
    const { startDate, endDate } = dateRange;
    const fmtDate = (iso: string) => { const [y,m,d] = iso.split("-"); return `${m}/${d}/${y}`; };

    const adsUrl =
      `https://ui.ads.microsoft.com/campaign/vnext/campaigns` +
      `?startDate=${encodeURIComponent(fmtDate(startDate))}&endDate=${encodeURIComponent(fmtDate(endDate))}`;

    const tab = window.open(adsUrl, "_blank");
    if (!tab) { setScrapeStatus("Popup blocked — allow popups and try again"); setIsScraping(false); return; }

    setScrapeStatus("Waiting for Microsoft Ads to load... (15–30 seconds)");

    const result = await new Promise<MicrosoftData | null>((resolve) => {
      const timeout = setTimeout(() => {
        setScrapeStatus("Timed out — make sure you are logged in to Microsoft Ads");
        resolve(null);
      }, 60_000);

      const handler = async (event: MessageEvent) => {
        if (!event.data || event.data.source !== "schumacher_ms_scraper") return;
        clearTimeout(timeout);
        window.removeEventListener("message", handler);

        const raw = event.data.payload as Record<string, string>;
        if (!raw || raw.error) { setScrapeStatus(`Error: ${raw?.error ?? "unknown"}`); resolve(null); return; }

        setScrapeStatus("Saving...");
        const p = (v: string) => parseFloat((v||"0").replace(/[$,%]/g,"").replace(/,/g,"")) || 0;
        const spend = p(raw.spend), impressions = p(raw.impressions), clicks = p(raw.clicks);
        const ctr = p(raw.ctr), cpc = p(raw.cpc), conversions = p(raw.conversions);
        const payload = {
          start_date: startDate, end_date: endDate, spend, impressions, clicks, ctr, cpc,
          conversions, cost_per_conversion: conversions > 0 ? spend / conversions : 0,
          leads: conversions, cost_per_lead: conversions > 0 ? spend / conversions : 0,
          campaigns: raw.campaigns ? JSON.parse(raw.campaigns) : [],
        };
        try {
          await fetch(`${API_BASE}/api/microsoft/ingest`, {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });
          setScrapeStatus("Done ✓");
          resolve({ ...payload, connected: true });
        } catch(e) { setScrapeStatus(`Save failed: ${e}`); resolve(null); }
      };
      window.addEventListener("message", handler);
    });

    if (result) setData(result);
    setIsScraping(false);
  };

  const connected = !!data?.connected;
  const scrapedAt = data?.scraped_at ? new Date(data.scraped_at).toLocaleString() : null;

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
        {/* Header row */}
        <div className="flex items-center gap-3">
          <div className={`w-3 h-3 rounded-full ${connected ? "bg-cyan-500" : "bg-gray-400"}`} />
          {connected ? (
            <span className="flex items-center gap-1 text-xs px-2 py-0.5 rounded bg-cyan-50 text-cyan-700 border border-cyan-200">
              <CheckCircle2 className="h-3 w-3" /> Scraped
            </span>
          ) : (
            <span className="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-500">Not Scraped</span>
          )}
          {scrapedAt && (
            <span className="flex items-center gap-1 text-xs text-gray-400">
              <Clock className="h-3 w-3" /> {scrapedAt}
            </span>
          )}
          <button
            onClick={handleScrape}
            disabled={isScraping}
            className={`ml-auto flex items-center gap-1.5 text-sm font-medium px-4 py-2 rounded-md border transition-all
              ${isScraping
                ? "bg-gray-50 text-gray-400 border-gray-200 cursor-not-allowed"
                : "bg-cyan-50 text-cyan-700 border-cyan-200 hover:bg-cyan-100 hover:border-cyan-300 cursor-pointer"
              }`}
          >
            <ScanSearch className="h-4 w-4" />
            {isScraping ? "Scraping..." : connected ? "Re-Scrape" : "Scrape Microsoft Ads"}
          </button>
        </div>

        {/* Status bar */}
        {isScraping && scrapeStatus && (
          <div className="text-sm text-cyan-700 bg-cyan-50 border border-cyan-200 rounded px-4 py-3 flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-cyan-500 animate-pulse" />
            {scrapeStatus}
          </div>
        )}
        {!isScraping && scrapeStatus === "Done ✓" && (
          <div className="text-sm text-green-700 bg-green-50 border border-green-200 rounded px-4 py-3 flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4" /> Scrape complete — data updated
          </div>
        )}

        {/* KPI Cards */}
        {connected && data ? (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
              <MetricCard title="Spend" value={formatCurrency(data.spend)}
                icon={<DollarSign className="h-4 w-4" />} className="border-l-4 border-l-cyan-500" />
              <MetricCard title="Leads / Conversions" value={formatNumber(data.leads)}
                icon={<UserPlus className="h-4 w-4" />} className="border-l-4 border-l-cyan-500" />
              <MetricCard title="Cost / Lead" value={formatCurrency(data.cost_per_lead)}
                invertTrend icon={<Users className="h-4 w-4" />} className="border-l-4 border-l-cyan-500" />
              <MetricCard title="Clicks" value={formatNumber(data.clicks)}
                icon={<MousePointerClick className="h-4 w-4" />} className="border-l-4 border-l-cyan-500" />
              <MetricCard title="Avg. CPC" value={formatCurrency(data.cpc)}
                invertTrend icon={<DollarSign className="h-4 w-4" />} className="border-l-4 border-l-cyan-500" />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <MetricCard title="Impressions" value={formatNumber(data.impressions)}
                icon={<Monitor className="h-4 w-4" />} className="border-l-4 border-l-cyan-500" />
              <MetricCard title="CTR" value={`${data.ctr.toFixed(2)}%`}
                icon={<MousePointerClick className="h-4 w-4" />} className="border-l-4 border-l-cyan-500" />
              <MetricCard title="Conversions" value={formatNumber(data.conversions)}
                icon={<Target className="h-4 w-4" />} className="border-l-4 border-l-cyan-500" />
            </div>

            {/* Campaign breakdown */}
            {data.campaigns && data.campaigns.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold mb-3 text-gray-700">Campaign Breakdown</h3>
                <div className="rounded-lg border overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
                      <tr>
                        <th className="px-4 py-2 text-left">Campaign</th>
                        <th className="px-4 py-2 text-right">Spend</th>
                        <th className="px-4 py-2 text-right">Clicks</th>
                        <th className="px-4 py-2 text-right">Impressions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {data.campaigns.map((c, i) => (
                        <tr key={i} className="hover:bg-gray-50">
                          <td className="px-4 py-2 font-medium text-gray-800">{c.name || "—"}</td>
                          <td className="px-4 py-2 text-right text-gray-600">{c.spend || "—"}</td>
                          <td className="px-4 py-2 text-right text-gray-600">{c.clicks || "—"}</td>
                          <td className="px-4 py-2 text-right text-gray-600">{c.impressions || "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </>
        ) : (
          /* Empty state */
          <div className="flex flex-col items-center justify-center py-20">
            <div className="rounded-full bg-cyan-50 p-6 mb-6">
              <Monitor className="h-12 w-12 text-cyan-500" />
            </div>
            <h2 className="text-xl font-bold mb-2">No Microsoft Ads data yet</h2>
            <p className="text-muted-foreground text-center max-w-md mb-6">
              Click <strong>Scrape Microsoft Ads</strong> above to open the Microsoft Ads UI,
              extract performance data for the selected date range, and populate this dashboard.
              Make sure you are logged in to Microsoft Ads first.
            </p>
            <button
              onClick={handleScrape}
              disabled={isScraping}
              className="flex items-center gap-2 bg-cyan-600 text-white px-5 py-2.5 rounded-lg hover:bg-cyan-700 transition-colors font-medium"
            >
              <ScanSearch className="h-4 w-4" />
              {isScraping ? "Scraping..." : "Scrape Microsoft Ads"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
