"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { RefreshCw, Download, ChevronDown } from "lucide-react";
import { DateRangeSelector } from "@/components/dashboard/DateRangeSelector";
import type { DateRange } from "@/lib/date-range";

interface HeaderProps {
  title: string;
  subtitle?: string;
  onRefresh?: () => void;
  isLoading?: boolean;
  // Date range props (optional — pages without date filtering can omit)
  selectedPreset?: string;
  customRange?: DateRange | null;
  onPresetChange?: (preset: string) => void;
  onCustomRangeChange?: (range: DateRange) => void;
}

export function Header({
  title,
  subtitle,
  onRefresh,
  isLoading = false,
  selectedPreset,
  customRange,
  onPresetChange,
  onCustomRangeChange,
}: HeaderProps) {
  const [isExportOpen, setIsExportOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  const handleExportActiveAds = async () => {
    setIsExporting(true);
    try {
      const response = await fetch("http://localhost:8001/api/reports/active-ads/csv");
      if (!response.ok) throw new Error("Export failed");

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `schumacher_active_ads_${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error("Export failed:", error);
    } finally {
      setIsExporting(false);
      setIsExportOpen(false);
    }
  };

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b bg-background px-6">
      <div>
        <h1 className="text-xl font-semibold">{title}</h1>
        {subtitle && (
          <p className="text-sm text-muted-foreground">{subtitle}</p>
        )}
      </div>
      <div className="flex items-center gap-3">
        {/* Export Dropdown */}
        <div className="relative">
          <Button
            variant="outline"
            size="sm"
            className="gap-2"
            onClick={() => setIsExportOpen(!isExportOpen)}
          >
            <Download className="h-4 w-4" />
            Export
            <ChevronDown className={cn("h-3 w-3 transition-transform", isExportOpen && "rotate-180")} />
          </Button>

          {isExportOpen && (
            <>
              {/* Backdrop to close dropdown */}
              <div
                className="fixed inset-0 z-40"
                onClick={() => setIsExportOpen(false)}
              />

              {/* Dropdown menu */}
              <div className="absolute right-0 top-full mt-1 z-50 w-64 rounded-md border bg-popover p-1 shadow-md">
                <button
                  className="flex w-full items-center gap-2 rounded-sm px-3 py-2 text-sm hover:bg-accent hover:text-accent-foreground disabled:opacity-50"
                  onClick={handleExportActiveAds}
                  disabled={isExporting}
                >
                  <Download className={cn("h-4 w-4", isExporting && "animate-pulse")} />
                  <div className="text-left">
                    <div className="font-medium">Active Ads Report</div>
                    <div className="text-xs text-muted-foreground">
                      CSV with all 204 truly active ads
                    </div>
                  </div>
                </button>
              </div>
            </>
          )}
        </div>

        {/* Date Range Selector */}
        {selectedPreset && onPresetChange && onCustomRangeChange && (
          <DateRangeSelector
            selectedPreset={selectedPreset}
            customRange={customRange ?? null}
            onPresetChange={onPresetChange}
            onCustomRangeChange={onCustomRangeChange}
          />
        )}

        {/* Refresh Button */}
        {onRefresh && (
          <Button
            variant="outline"
            size="sm"
            onClick={onRefresh}
            disabled={isLoading}
            className="gap-2"
          >
            <RefreshCw
              className={cn("h-4 w-4", isLoading && "animate-spin")}
            />
            Refresh
          </Button>
        )}
      </div>
    </header>
  );
}

// Helper for conditional classes
function cn(...classes: (string | boolean | undefined)[]) {
  return classes.filter(Boolean).join(" ");
}
