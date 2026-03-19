"use client";

import { useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  Layers,
  Megaphone,
  Layout,
  Image,
  Loader2,
} from "lucide-react";
import { ActiveCampaign, ActiveAdSet, ActiveAd } from "@/lib/api";

interface ActiveAdsTreeProps {
  totalActiveAds: number;
  threshold: number;
  campaigns: ActiveCampaign[];
  isLoading: boolean;
  onOpen: () => void;
}

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

function AdRow({ ad }: { ad: ActiveAd }) {
  return (
    <div className="py-1.5 px-2 text-xs text-gray-600">
      <div className="flex items-center gap-2">
        <Image className="h-3 w-3 text-gray-300 shrink-0" />
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

function AdSetRow({ adset }: { adset: ActiveAdSet }) {
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
            <p className="text-xs text-gray-400 py-1 px-2">No active ads</p>
          ) : (
            adset.ads.map((ad) => <AdRow key={ad.id} ad={ad} />)
          )}
        </div>
      )}
    </div>
  );
}

function CampaignRow({ campaign }: { campaign: ActiveCampaign }) {
  const [open, setOpen] = useState(false);
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
            <span>{campaign.adset_count} ad {campaign.adset_count === 1 ? "set" : "sets"}</span>
            <span className="font-medium text-gray-600">{campaign.ad_count} active {campaign.ad_count === 1 ? "ad" : "ads"}</span>
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
            <p className="text-xs text-gray-400 py-2 px-3">No active ad sets</p>
          ) : (
            campaign.adsets.map((adset) => (
              <AdSetRow key={adset.id} adset={adset} />
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
}: ActiveAdsTreeProps) {
  const [open, setOpen] = useState(false);
  const atThreshold = totalActiveAds >= threshold * 0.9;

  const handleToggle = () => {
    const next = !open;
    setOpen(next);
    if (next && campaigns.length === 0 && !isLoading) {
      onOpen();
    }
  };

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
          <span className="font-semibold text-gray-800">Active Ads</span>
          <span
            className={`text-sm font-medium ${
              atThreshold ? "text-red-600" : "text-gray-600"
            }`}
          >
            {totalActiveAds} / {threshold}
          </span>
          {atThreshold && (
            <span className="text-xs font-medium text-red-500 bg-red-100 px-2 py-0.5 rounded-full">
              Near limit
            </span>
          )}
        </div>
        <span className="text-xs text-gray-400 shrink-0">
          {open ? "Collapse" : "View breakdown"}
        </span>
      </button>

      {/* Tree body */}
      {open && (
        <div className="border-t border-gray-100 px-4 py-4">
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
                {campaigns.length} active {campaigns.length === 1 ? "campaign" : "campaigns"} · {totalActiveAds} active {totalActiveAds === 1 ? "ad" : "ads"} · KPIs = last 30 days · <code className="bg-gray-100 px-1 rounded">status = ACTIVE</code> (includes learning &amp; in review)
              </p>
              {campaigns.map((campaign) => (
                <CampaignRow key={campaign.id} campaign={campaign} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
