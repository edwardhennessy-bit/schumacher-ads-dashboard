"use client";

import { useState, useRef, useCallback, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Campaign, formatCurrency, formatNumber, formatPercent } from "@/lib/mock-data";
import { cn } from "@/lib/utils";
import {
  ChevronUp,
  ChevronDown,
  ChevronsUpDown,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

interface CampaignTableProps {
  campaigns: Campaign[];
  title?: string;
}

type SortKey = "name" | "status" | "spend" | "clicks" | "ctr" | "leads" | "cpl" | "leadRate" | "conversions";
type SortDir = "asc" | "desc";

interface ColumnDef {
  key: SortKey;
  label: string;
  defaultWidth: number;
  minWidth: number;
  align?: "left" | "right";
}

const COLUMNS: ColumnDef[] = [
  { key: "name", label: "Campaign", defaultWidth: 240, minWidth: 120, align: "left" },
  { key: "status", label: "Status", defaultWidth: 90, minWidth: 70, align: "left" },
  { key: "spend", label: "Spend", defaultWidth: 100, minWidth: 70, align: "right" },
  { key: "clicks", label: "Clicks", defaultWidth: 80, minWidth: 60, align: "right" },
  { key: "ctr", label: "CTR", defaultWidth: 70, minWidth: 50, align: "right" },
  { key: "leads", label: "Leads", defaultWidth: 70, minWidth: 50, align: "right" },
  { key: "cpl", label: "CPL", defaultWidth: 90, minWidth: 60, align: "right" },
  { key: "leadRate", label: "Lead Rate", defaultWidth: 90, minWidth: 60, align: "right" },
  { key: "conversions", label: "Conv.", defaultWidth: 70, minWidth: 50, align: "right" },
];

const PAGE_SIZE_OPTIONS = [10, 25, 50];

/** Map a column key to the actual numeric/string value on the campaign. */
function getCampaignValue(campaign: Campaign, key: SortKey): number | string {
  switch (key) {
    case "name": return campaign.name;
    case "status": return campaign.status;
    case "spend": return campaign.spend;
    case "clicks": return campaign.clicks;
    case "ctr": return campaign.ctr;
    case "leads": return campaign.leads;
    case "cpl": return campaign.costPerLead;
    case "leadRate": return campaign.leadRate;
    case "conversions": return campaign.conversions;
  }
}

/**
 * Determine performance tier for a campaign based on CPL relative to the group.
 * - "high" = CPL well below average (good) → green
 * - "low"  = CPL well above average (bad) → red
 * - "mid"  = in the middle → no highlight
 */
function getPerformanceTier(
  campaign: Campaign,
  avgCpl: number
): "high" | "mid" | "low" {
  if (campaign.spend <= 0 || campaign.leads <= 0) return "mid";
  const cpl = campaign.costPerLead;
  if (cpl < avgCpl * 0.7) return "high";
  if (cpl > avgCpl * 1.3) return "low";
  return "mid";
}

function SortIcon({ colKey, sortKey, sortDir }: { colKey: SortKey; sortKey: SortKey; sortDir: SortDir }) {
  if (sortKey !== colKey) return <ChevronsUpDown className="h-3 w-3 ml-1 text-gray-400 inline shrink-0" />;
  return sortDir === "desc"
    ? <ChevronDown className="h-3 w-3 ml-1 text-[#f27038] inline shrink-0" />
    : <ChevronUp className="h-3 w-3 ml-1 text-[#f27038] inline shrink-0" />;
}

export function CampaignTable({
  campaigns,
  title = "Campaign Performance",
}: CampaignTableProps) {
  // Column widths for resizing
  const [colWidths, setColWidths] = useState<Record<string, number>>(() => {
    const initial: Record<string, number> = {};
    COLUMNS.forEach((col) => { initial[col.key] = col.defaultWidth; });
    return initial;
  });

  // Sort / filter / pagination state
  const [sortKey, setSortKey] = useState<SortKey>("spend");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [filterActive, setFilterActive] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Resize handling
  const resizingRef = useRef<{ key: string; startX: number; startWidth: number } | null>(null);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent, colKey: string) => {
      e.preventDefault();
      e.stopPropagation(); // don't trigger sort click
      resizingRef.current = { key: colKey, startX: e.clientX, startWidth: colWidths[colKey] };

      const handleMouseMove = (ev: MouseEvent) => {
        if (!resizingRef.current) return;
        const diff = ev.clientX - resizingRef.current.startX;
        const col = COLUMNS.find((c) => c.key === resizingRef.current!.key);
        const minW = col?.minWidth ?? 50;
        const newWidth = Math.max(minW, resizingRef.current.startWidth + diff);
        setColWidths((prev) => ({ ...prev, [resizingRef.current!.key]: newWidth }));
      };

      const handleMouseUp = () => {
        resizingRef.current = null;
        document.removeEventListener("mousemove", handleMouseMove);
        document.removeEventListener("mouseup", handleMouseUp);
      };

      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
    },
    [colWidths]
  );

  const handleSort = (key: SortKey) => {
    if (resizingRef.current) return; // ignore sort clicks during resize
    if (sortKey === key) {
      setSortDir(d => d === "desc" ? "asc" : "desc");
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
    setCurrentPage(1);
  };

  const getStatusBadge = (status: Campaign["status"]) => {
    switch (status) {
      case "ACTIVE":
        return <Badge className="bg-green-100 text-green-800 hover:bg-green-100">Active</Badge>;
      case "PAUSED":
        return <Badge variant="secondary">Paused</Badge>;
      case "ARCHIVED":
        return <Badge variant="outline">Archived</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  // Average CPL for performance highlighting
  const avgCpl = useMemo(() => {
    const withLeads = campaigns.filter(c => c.leads > 0 && c.spend > 0);
    return withLeads.length > 0
      ? withLeads.reduce((sum, c) => sum + c.costPerLead, 0) / withLeads.length
      : 0;
  }, [campaigns]);

  // Filtered + sorted campaigns
  const filteredSorted = useMemo(() => {
    const base = filterActive
      ? campaigns.filter(c => c.status === "ACTIVE")
      : campaigns;
    return [...base].sort((a, b) => {
      const aVal = getCampaignValue(a, sortKey);
      const bVal = getCampaignValue(b, sortKey);
      if (typeof aVal === "string" && typeof bVal === "string") {
        return sortDir === "desc" ? bVal.localeCompare(aVal) : aVal.localeCompare(bVal);
      }
      return sortDir === "desc"
        ? (bVal as number) - (aVal as number)
        : (aVal as number) - (bVal as number);
    });
  }, [campaigns, filterActive, sortKey, sortDir]);

  const totalPages = Math.max(1, Math.ceil(filteredSorted.length / pageSize));
  const paged = filteredSorted.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  const getRowClasses = (tier: "high" | "mid" | "low") => {
    switch (tier) {
      case "high": return "bg-green-50/60 hover:bg-green-100/60";
      case "low": return "bg-red-50/60 hover:bg-red-100/60";
      default: return "hover:bg-muted/50";
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <CardTitle className="text-lg">{title}</CardTitle>
          {avgCpl > 0 && (
            <span className="text-xs text-muted-foreground">
              Avg CPL: {formatCurrency(avgCpl)} · CPL &gt;30% below avg is{" "}
              <span className="text-green-600 font-medium">green</span>, &gt;30% above is{" "}
              <span className="text-red-500 font-medium">red</span>
            </span>
          )}
        </div>

        {/* Toolbar */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
          <div className="flex items-center gap-4">
            <span className="text-xs text-gray-500">
              {filteredSorted.length} of {campaigns.length} campaigns
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
      </CardHeader>

      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm" style={{ tableLayout: "fixed" }}>
            <colgroup>
              {COLUMNS.map((col) => (
                <col key={col.key} style={{ width: colWidths[col.key] }} />
              ))}
            </colgroup>
            <thead>
              <tr className="border-b">
                {COLUMNS.map((col) => (
                  <th
                    key={col.key}
                    onClick={() => handleSort(col.key)}
                    className={cn(
                      "relative px-3 py-3 text-xs font-medium text-muted-foreground select-none cursor-pointer hover:bg-gray-50 transition-colors",
                      col.align === "right" ? "text-right" : "text-left"
                    )}
                  >
                    <span className="inline-flex items-center gap-0.5">
                      {col.label}
                      <SortIcon colKey={col.key} sortKey={sortKey} sortDir={sortDir} />
                    </span>
                    {/* Resize handle — stopPropagation so it doesn't trigger sort */}
                    <div
                      className="absolute right-0 top-0 bottom-0 w-2 cursor-col-resize hover:bg-gray-300/50 active:bg-gray-400/50"
                      onMouseDown={(e) => handleMouseDown(e, col.key)}
                    />
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {paged.length === 0 ? (
                <tr>
                  <td colSpan={COLUMNS.length} className="px-3 py-8 text-center text-gray-400 text-xs">
                    No campaigns match the current filter.
                  </td>
                </tr>
              ) : paged.map((campaign, idx) => {
                const tier = getPerformanceTier(campaign, avgCpl);
                return (
                  <tr
                    key={`${campaign.id}-${idx}`}
                    className={cn("border-b transition-colors", getRowClasses(tier))}
                  >
                    {/* Campaign Name */}
                    <td className="px-3 py-3 font-medium">
                      <div className="flex flex-col overflow-hidden">
                        <span className="truncate">{campaign.name}</span>
                        <span className="text-xs text-muted-foreground truncate">
                          {campaign.objective.replace(/_/g, " ")}
                        </span>
                      </div>
                    </td>
                    {/* Status */}
                    <td className="px-3 py-3">{getStatusBadge(campaign.status)}</td>
                    {/* Spend */}
                    <td className="px-3 py-3 text-right font-medium tabular-nums">
                      {formatCurrency(campaign.spend)}
                    </td>
                    {/* Clicks */}
                    <td className="px-3 py-3 text-right tabular-nums">
                      {formatNumber(campaign.clicks)}
                    </td>
                    {/* CTR */}
                    <td className="px-3 py-3 text-right tabular-nums">
                      {formatPercent(campaign.ctr)}
                    </td>
                    {/* Leads */}
                    <td className={cn(
                      "px-3 py-3 text-right font-semibold tabular-nums",
                      tier === "high" && "text-green-700",
                      tier === "low" && "text-red-600"
                    )}>
                      {campaign.leads}
                    </td>
                    {/* CPL */}
                    <td className={cn(
                      "px-3 py-3 text-right font-semibold tabular-nums",
                      tier === "high" && "text-green-700",
                      tier === "low" && "text-red-600"
                    )}>
                      {campaign.costPerLead > 0 ? formatCurrency(campaign.costPerLead) : "—"}
                    </td>
                    {/* Lead Rate */}
                    <td className={cn(
                      "px-3 py-3 text-right font-semibold tabular-nums",
                      tier === "high" && "text-green-700",
                      tier === "low" && "text-red-600"
                    )}>
                      {formatPercent(campaign.leadRate)}
                    </td>
                    {/* Conversions */}
                    <td className="px-3 py-3 text-right tabular-nums">
                      {campaign.conversions}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-4 pt-3 border-t">
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
      </CardContent>
    </Card>
  );
}
