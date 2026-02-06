"use client";

import { useState, useRef, useCallback } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Campaign, formatCurrency, formatNumber, formatPercent } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

interface CampaignTableProps {
  campaigns: Campaign[];
  title?: string;
}

interface ColumnDef {
  key: string;
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
  // Campaigns with no spend or no leads are neutral
  if (campaign.spend <= 0 || campaign.leads <= 0) return "mid";

  const cpl = campaign.costPerLead;

  // More than 30% below average CPL → high performer (green)
  if (cpl < avgCpl * 0.7) return "high";
  // More than 30% above average CPL → low performer (red)
  if (cpl > avgCpl * 1.3) return "low";

  return "mid";
}

export function CampaignTable({
  campaigns,
  title = "Campaign Performance",
}: CampaignTableProps) {
  // Column widths state for resizing
  const [colWidths, setColWidths] = useState<Record<string, number>>(() => {
    const initial: Record<string, number> = {};
    COLUMNS.forEach((col) => {
      initial[col.key] = col.defaultWidth;
    });
    return initial;
  });

  // Resize handling
  const resizingRef = useRef<{
    key: string;
    startX: number;
    startWidth: number;
  } | null>(null);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent, colKey: string) => {
      e.preventDefault();
      resizingRef.current = {
        key: colKey,
        startX: e.clientX,
        startWidth: colWidths[colKey],
      };

      const handleMouseMove = (ev: MouseEvent) => {
        if (!resizingRef.current) return;
        const diff = ev.clientX - resizingRef.current.startX;
        const col = COLUMNS.find((c) => c.key === resizingRef.current!.key);
        const minW = col?.minWidth ?? 50;
        const newWidth = Math.max(minW, resizingRef.current.startWidth + diff);
        setColWidths((prev) => ({
          ...prev,
          [resizingRef.current!.key]: newWidth,
        }));
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

  const getStatusBadge = (status: Campaign["status"]) => {
    switch (status) {
      case "ACTIVE":
        return (
          <Badge className="bg-green-100 text-green-800 hover:bg-green-100">
            Active
          </Badge>
        );
      case "PAUSED":
        return <Badge variant="secondary">Paused</Badge>;
      case "ARCHIVED":
        return <Badge variant="outline">Archived</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  // Calculate average CPL across campaigns that have leads
  const campaignsWithLeads = campaigns.filter(
    (c) => c.leads > 0 && c.spend > 0
  );
  const avgCpl =
    campaignsWithLeads.length > 0
      ? campaignsWithLeads.reduce((sum, c) => sum + c.costPerLead, 0) /
        campaignsWithLeads.length
      : 0;

  const getRowClasses = (tier: "high" | "mid" | "low") => {
    switch (tier) {
      case "high":
        return "bg-green-50/60 hover:bg-green-100/60";
      case "low":
        return "bg-red-50/60 hover:bg-red-100/60";
      default:
        return "hover:bg-muted/50";
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">{title}</CardTitle>
          {avgCpl > 0 && (
            <span className="text-xs text-muted-foreground">
              Avg CPL: {formatCurrency(avgCpl)} · Campaigns with CPL &gt;30%
              below avg are{" "}
              <span className="text-green-600 font-medium">green</span>, &gt;30%
              above are{" "}
              <span className="text-red-500 font-medium">red</span>
            </span>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm" style={{ tableLayout: "fixed" }}>
            <colgroup>
              {COLUMNS.map((col) => (
                <col
                  key={col.key}
                  style={{ width: colWidths[col.key] }}
                />
              ))}
            </colgroup>
            <thead>
              <tr className="border-b">
                {COLUMNS.map((col) => (
                  <th
                    key={col.key}
                    className={cn(
                      "relative px-3 py-3 text-xs font-medium text-muted-foreground select-none",
                      col.align === "right" ? "text-right" : "text-left"
                    )}
                  >
                    {col.label}
                    {/* Resize handle */}
                    <div
                      className="absolute right-0 top-0 bottom-0 w-2 cursor-col-resize hover:bg-gray-300/50 active:bg-gray-400/50"
                      onMouseDown={(e) => handleMouseDown(e, col.key)}
                    />
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {campaigns.map((campaign) => {
                const tier = getPerformanceTier(campaign, avgCpl);
                return (
                  <tr
                    key={campaign.id}
                    className={cn(
                      "border-b transition-colors",
                      getRowClasses(tier)
                    )}
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
                    <td className="px-3 py-3">
                      {getStatusBadge(campaign.status)}
                    </td>
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
                    <td
                      className={cn(
                        "px-3 py-3 text-right font-semibold tabular-nums",
                        tier === "high" && "text-green-700",
                        tier === "low" && "text-red-600"
                      )}
                    >
                      {campaign.leads}
                    </td>
                    {/* CPL */}
                    <td
                      className={cn(
                        "px-3 py-3 text-right font-semibold tabular-nums",
                        tier === "high" && "text-green-700",
                        tier === "low" && "text-red-600"
                      )}
                    >
                      {campaign.costPerLead > 0
                        ? formatCurrency(campaign.costPerLead)
                        : "—"}
                    </td>
                    {/* Lead Rate */}
                    <td
                      className={cn(
                        "px-3 py-3 text-right font-semibold tabular-nums",
                        tier === "high" && "text-green-700",
                        tier === "low" && "text-red-600"
                      )}
                    >
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
      </CardContent>
    </Card>
  );
}
