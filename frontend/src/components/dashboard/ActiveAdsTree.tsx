"use client";

import { useState, useEffect } from "react";
import {
  ChevronDown,
  ChevronRight,
  Layers,
  Megaphone,
  Layout,
  Image,
  FileText,
  Loader2,
} from "lucide-react";
import { ActiveCampaign, ActiveAdSet, ActiveAd } from "@/lib/api";
import { AiInsightsPanel } from "@/components/dashboard/AiInsightsPanel";
import { AskJarvisButton } from "@/components/dashboard/JarvisDrawer";

interface ActiveAdsTreeProps {
  totalActiveAds: number;
  threshold?: number;
  campaigns: ActiveCampaign[];
  isLoading: boolean;
  onOpen: (startDate: string, endDate: string, mode: "active" | "with_spend") => void;
  startDate: string;
  endDate: string;
  onDateChange: (startDate: string, endDate: string) => void;
  platform?: "meta" | "google" | "microsoft";
}

// --- Date preset helpers ---
type Preset = {
  label: string;
  value: string;
  getDates: () => { start: string; end: string };
};

function fmtDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

const today = () => new Date();

function startOfMonth(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), 1);
}

function shiftBack(start: string, end: string): { start: string; end: string } {
  const s = new Date(start);
  const e = new Date(end);
  const diffMs = e.getTime() - s.getTime();
  const newEnd = new Date(s.getTime() - 1);
  const newStart = new Date(newEnd.getTime() - diffMs);
  return { start: fmtDate(newStart), end: fmtDate(newEnd) };
}

const PRESETS: Preset[] = [
  {
    label: "MTD",
    value: "mtd",
    getDates: () => {
      const t = today();
      return { start: fmtDate(startOfMonth(t)), end: fmtDate(t) };
    },
  },
  {
    label: "Last 7 Days",
    value: "7d",
    getDates: () => {
      const t = today();
      const s = new Date(t);
      s.setDate(s.getDate() - 7);
      return { start: fmtDate(s), end: fmtDate(t) };
    },
  },
  {
    label: "Last 14 Days",
    value: "14d",
    getDates: () => {
      const t = today();
      const s = new Date(t);
      s.setDate(s.getDate() - 14);
      return { start: fmtDate(s), end: fmtDate(t) };
    },
  },
  {
    label: "Last 30 Days",
    value: "30d",
    getDates: () => {
      const t = today();
      const s = new Date(t);
      s.setDate(s.getDate() - 30);
      return { start: fmtDate(s), end: fmtDate(t) };
    },
  },
  {
    label: "Last 60 Days",
    value: "60d",
    getDates: () => {
      const t = today();
      const s = new Date(t);
      s.setDate(s.getDate() - 60);
      return { start: fmtDate(s), end: fmtDate(t) };
    },
  },
  {
    label: "Last 90 Days",
    value: "90d",
    getDates: () => {
      const t = today();
      const s = new Date(t);
      s.setDate(s.getDate() - 90);
      return { start: fmtDate(s), end: fmtDate(t) };
    },
  },
  {
    label: "Last Month",
    value: "last_month",
    getDates: () => {
      const t = today();
      const firstOfThis = startOfMonth(t);
      const lastOfPrev = new Date(firstOfThis.getTime() - 86400000);
      const firstOfPrev = startOfMonth(lastOfPrev);
      return { start: fmtDate(firstOfPrev), end: fmtDate(lastOfPrev) };
    },
  },
];

// --- KPI helpers ---
function fmt$(n?: number) {
  if (n == null || n === 0) return null;
  return n >= 1000 ? `$${(n / 1000).toFixed(1)}k` : `$${n.toFixed(0)}`;
}

function fmtNum(n?: number) {
  if (n == null || n === 0) return null;
  return n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n);
}

function fmtPct(n?: number) {
  if (n == null || n === 0) return null;
  return `${n.toFixed(2)}%`;
}

interface KpiBarProps {
  spend?: number;
  clicks?: number;
  ctr?: number;
  cpc?: number;
  leads?: number;
  cost_per_lead?: number;
  size?: "sm" | "xs";
}

function KpiBar({ spend, clicks, ctr, cpc, leads, cost_per_lead, size = "sm" }: KpiBarProps) {
  const hasAny = spend || clicks || ctr || cpc || leads;
  if (!hasAny) return null;

  const pill = size === "xs"
    ? "text-xs px-1.5 py-0.5 rounded"
    : "text-xs px-2 py-0.5 rounded";

  return (
    <div className="flex flex-wrap items-center gap-1.5 mt-1">
      {spend ? (
        <span className={`${pill} bg-gray-100 text-gray-600 font-medium`}>
          {fmt$(spend)} spend
        </span>
      ) : null}
      {clicks ? (
        <span className={`${pill} bg-gray-100 text-gray-600 font-medium`}>
          {fmtNum(clicks)} clicks
        </span>
      ) : null}
      {ctr ? (
        <span className={`${pill} bg-gray-100 text-gray-600 font-medium`}>
          {fmtPct(ctr)} CTR
        </span>
      ) : null}
      {cpc ? (
        <span className={`${pill} bg-gray-100 text-gray-600 font-medium`}>
          {fmt$(cpc)} CPC
        </span>
      ) : null}
      {leads ? (
        <span className={`${pill} bg-green-50 text-green-700 font-medium`}>
          {leads} lead{leads !== 1 ? "s" : ""}
        </span>
      ) : null}
      {cost_per_lead && leads ? (
        <span className={`${pill} bg-blue-50 text-blue-700 font-medium`}>
          {fmt$(cost_per_lead)} CPL
        </span>
      ) : null}
    </div>
  );
}

function AdRow({ ad, platform }: { ad: ActiveAd; platform?: "meta" | "google" | "microsoft" }) {
  const AdIcon = platform === "meta" ? Image : FileText;
  return (
    <div className="py-1.5 px-2 text-xs text-gray-600">
      <div className="flex items-center gap-2">
        <AdIcon className="h-3 w-3 text-gray-300 shrink-0" />
        <span className="truncate font-medium">{ad.name}</span>
      </div>
      <div className="ml-5">
        <KpiBar
          spend={ad.spend}
          clicks={ad.clicks}
          ctr={ad.ctr}
          cpc={ad.cpc}
          leads={ad.leads}
          cost_per_lead={ad.cost_per_lead}
          size="xs"
        />
      </div>
    </div>
  );
}

function AdSetRow({ adset, platform }: { adset: ActiveAdSet; platform?: "meta" | "google" | "microsoft" }) {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full text-left py-1.5 px-3 rounded hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          {open ? (
            <ChevronDown className="h-3.5 w-3.5 text-gray-400 shrink-0" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5 text-gray-400 shrink-0" />
          )}
          <Layout className="h-3.5 w-3.5 text-blue-400 shrink-0" />
          <span className="flex-1 text-sm text-gray-700 truncate">{adset.name}</span>
          <span className="text-xs text-gray-400 shrink-0 ml-2">
            {adset.ad_count} {adset.ad_count === 1 ? "ad" : "ads"}
          </span>
        </div>
        <div className="ml-6">
          <KpiBar
            spend={adset.spend}
            clicks={adset.clicks}
            ctr={adset.ctr}
            cpc={adset.cpc}
            leads={adset.leads}
            cost_per_lead={adset.cost_per_lead}
          />
        </div>
      </button>
      {open && (
        <div className="ml-8 border-l border-gray-100 pl-2 mb-1">
          {adset.ads.length === 0 ? (
            <p className="text-xs text-gray-400 py-1 px-2">No ads</p>
          ) : (
            adset.ads.map((ad) => <AdRow key={ad.id} ad={ad} platform={platform} />)
          )}
        </div>
      )}
    </div>
  );
}

function CampaignRow({ campaign, groupLabel, platform }: { campaign: ActiveCampaign; groupLabel: string; platform?: "meta" | "google" | "microsoft" }) {
  const [open, setOpen] = useState(false);
  const isPmax = campaign.is_pmax === true;
  const groupLabelSingular = groupLabel.endsWith("s") ? groupLabel.slice(0, -1) : groupLabel;
  const effectiveGroupLabel = isPmax ? "Asset Groups" : groupLabel;
  const effectiveGroupLabelSingular = isPmax ? "Asset Group" : groupLabelSingular;
  return (
    <div className="border border-gray-100 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full text-left px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors"
      >
        <div className="flex items-center gap-2">
          {open ? (
            <ChevronDown className="h-4 w-4 text-gray-400 shrink-0" />
          ) : (
            <ChevronRight className="h-4 w-4 text-gray-400 shrink-0" />
          )}
          <Megaphone className="h-4 w-4 text-indigo-400 shrink-0" />
          <span className="flex-1 text-sm font-medium text-gray-800 truncate">
            {campaign.name}
          </span>
          <div className="flex items-center gap-3 shrink-0 ml-2 text-xs text-gray-400">
            <span>{campaign.adset_count} {campaign.adset_count === 1 ? effectiveGroupLabelSingular : effectiveGroupLabel}</span>
            {!isPmax && (
              <span className="font-medium text-gray-600">{campaign.ad_count} {campaign.ad_count === 1 ? "ad" : "ads"}</span>
            )}
          </div>
        </div>
        <div className="ml-6">
          <KpiBar
            spend={campaign.spend}
            clicks={campaign.clicks}
            ctr={campaign.ctr}
            cpc={campaign.cpc}
            leads={campaign.leads}
            cost_per_lead={campaign.cost_per_lead}
          />
        </div>
      </button>
      {open && (
        <div className="px-2 py-1">
          {campaign.adsets.length === 0 ? (
            <p className="text-xs text-gray-400 py-2 px-3">No {effectiveGroupLabel.toLowerCase()}</p>
          ) : (
            campaign.adsets.map((adset) => (
              <AdSetRow key={adset.id} adset={adset} platform={platform} />
            ))
          )}
        </div>
      )}
    </div>
  );
}

export function ActiveAdsTree({
  totalActiveAds,
  threshold,
  campaigns,
  isLoading,
  onOpen,
  startDate,
  endDate,
  onDateChange,
  platform = "meta",
}: ActiveAdsTreeProps) {
  const groupLabel = platform === "meta" ? "Ad Sets" : "Ad Groups";
  // Threshold only applies on Meta (Meta has an ad account ad limit)
  const hasThreshold = platform === "meta" && threshold != null && threshold > 0;
  const [open, setOpen] = useState(false);
  const [selectedPreset, setSelectedPreset] = useState("mtd");
  const [adsMode, setAdsMode] = useState<"active" | "with_spend">("active");
  const [compareEnabled, setCompareEnabled] = useState(false);
  const [comparePreset, setComparePreset] = useState("30d");
  const [compareStart, setCompareStart] = useState<string | undefined>();
  const [compareEnd, setCompareEnd] = useState<string | undefined>();

  const atThreshold = hasThreshold && totalActiveAds >= (threshold ?? 0) * 0.9;

  const handleToggle = () => {
    const next = !open;
    setOpen(next);
    if (next && campaigns.length === 0 && !isLoading) {
      onOpen(startDate, endDate, adsMode);
    }
  };

  const handlePresetChange = (value: string) => {
    setSelectedPreset(value);
    const preset = PRESETS.find((p) => p.value === value);
    if (preset) {
      const { start, end } = preset.getDates();
      onDateChange(start, end);
      onOpen(start, end, adsMode);
    }
  };

  const handleAdsModeChange = (newMode: "active" | "with_spend") => {
    setAdsMode(newMode);
    onOpen(startDate, endDate, newMode);
  };

  const handleComparePresetChange = (value: string) => {
    setComparePreset(value);
    const preset = PRESETS.find((p) => p.value === value);
    if (preset) {
      const { start, end } = preset.getDates();
      setCompareStart(start);
      setCompareEnd(end);
    }
  };

  // When compare toggle turns on, compute comparison period as shifted-back version of main
  useEffect(() => {
    if (compareEnabled && startDate && endDate) {
      const shifted = shiftBack(startDate, endDate);
      setCompareStart(shifted.start);
      setCompareEnd(shifted.end);
    } else if (!compareEnabled) {
      setCompareStart(undefined);
      setCompareEnd(undefined);
    }
  }, [compareEnabled, startDate, endDate]);

  return (
    <div
      className={`rounded-xl border-2 ${
        atThreshold ? "border-red-200 bg-red-50/30" : "border-gray-200 bg-white"
      } overflow-hidden`}
    >
      {/* Header / toggle */}
      <button
        onClick={handleToggle}
        className="flex items-center gap-3 w-full text-left px-5 py-4 hover:bg-gray-50/60 transition-colors"
      >
        {open ? (
          <ChevronDown className="h-5 w-5 text-gray-400 shrink-0" />
        ) : (
          <ChevronRight className="h-5 w-5 text-gray-400 shrink-0" />
        )}
        <Layers
          className={`h-5 w-5 shrink-0 ${atThreshold ? "text-red-400" : "text-gray-400"}`}
        />
        <div className="flex-1 flex items-center gap-4">
          <span className="font-semibold text-gray-800">
            {adsMode === "with_spend" ? "Ads with Spend" : "Active Ads"}
          </span>
          <span
            className={`text-sm font-medium ${
              atThreshold ? "text-red-600" : "text-gray-600"
            }`}
          >
            {hasThreshold ? `${totalActiveAds} / ${threshold}` : totalActiveAds}
          </span>
          {atThreshold && (
            <span className="text-xs font-medium text-red-500 bg-red-100 px-2 py-0.5 rounded-full">
              Near limit
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0" onClick={(e) => e.stopPropagation()}>
          <AskJarvisButton section="active_ads" />
          <span className="text-xs text-gray-400">
            {open ? "Collapse" : "View breakdown"}
          </span>
        </div>
      </button>

      {/* Tree body */}
      {open && (
        <div className="border-t border-gray-100 px-4 py-4 space-y-4">
          {/* Date range controls */}
          <div className="flex items-center gap-3 bg-gray-50 rounded-lg px-3 py-2 flex-wrap">
            {/* Ads mode toggle */}
            <div className="flex rounded-md border border-gray-200 bg-white overflow-hidden shrink-0">
              <button
                onClick={() => handleAdsModeChange("active")}
                className={`text-xs px-2.5 py-1 transition-colors ${
                  adsMode === "active"
                    ? "bg-indigo-600 text-white font-medium"
                    : "text-gray-500 hover:bg-gray-50"
                }`}
              >
                Active Ads
              </button>
              <button
                onClick={() => handleAdsModeChange("with_spend")}
                className={`text-xs px-2.5 py-1 border-l border-gray-200 transition-colors ${
                  adsMode === "with_spend"
                    ? "bg-indigo-600 text-white font-medium"
                    : "text-gray-500 hover:bg-gray-50"
                }`}
              >
                Ads with Spend
              </button>
            </div>
            <select
              value={selectedPreset}
              onChange={(e) => handlePresetChange(e.target.value)}
              className="text-xs border border-gray-200 rounded-md px-2 py-1 bg-white focus:ring-1 focus:ring-indigo-300 outline-none"
            >
              {PRESETS.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
            <label className="flex items-center gap-1.5 text-xs text-gray-600 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={compareEnabled}
                onChange={(e) => setCompareEnabled(e.target.checked)}
                className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-300"
              />
              Compare to prior period
            </label>
            {compareEnabled && (
              <select
                value={comparePreset}
                onChange={(e) => handleComparePresetChange(e.target.value)}
                className="text-xs border border-gray-200 rounded-md px-2 py-1 bg-white focus:ring-1 focus:ring-indigo-300 outline-none"
              >
                {PRESETS.map((p) => (
                  <option key={p.value} value={p.value}>
                    {p.label}
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* AI Insights Panel */}
          <AiInsightsPanel
            startDate={startDate}
            endDate={endDate}
            compareStart={compareEnabled ? compareStart : undefined}
            compareEnd={compareEnabled ? compareEnd : undefined}
          />

          {/* Campaign tree */}
          <div>
            {isLoading ? (
              <div className="flex items-center gap-2 text-sm text-gray-500 py-4 justify-center">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading active ads…
              </div>
            ) : campaigns.length === 0 ? (
              <p className="text-sm text-gray-400 text-center py-4">
                No active campaigns found.
              </p>
            ) : (
              <div className="space-y-2">
                <p className="text-xs text-gray-400 mb-3">
                  {campaigns.length} {campaigns.length === 1 ? "campaign" : "campaigns"} · {totalActiveAds} {totalActiveAds === 1 ? "ad" : "ads"} · KPIs = selected period ·{" "}
                  {adsMode === "with_spend"
                    ? "all ads with spend > $0 (includes paused & archived)"
                    : <><code className="bg-gray-100 px-1 rounded">status = ACTIVE</code> (includes learning &amp; in review)</>
                  }
                </p>
                {campaigns.map((campaign) => (
                  <CampaignRow key={campaign.id} campaign={campaign} groupLabel={groupLabel} platform={platform} />
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
