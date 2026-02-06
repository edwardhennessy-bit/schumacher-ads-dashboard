"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Calendar, ChevronDown, Check } from "lucide-react";
import {
  DateRange,
  DATE_PRESETS,
  DEFAULT_PRESET,
  formatDateRangeLabel,
} from "@/lib/date-range";

interface DateRangeSelectorProps {
  selectedPreset: string;
  customRange: DateRange | null;
  onPresetChange: (preset: string) => void;
  onCustomRangeChange: (range: DateRange) => void;
}

export function DateRangeSelector({
  selectedPreset,
  customRange,
  onPresetChange,
  onCustomRangeChange,
}: DateRangeSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isCustomMode, setIsCustomMode] = useState(false);
  const [customStart, setCustomStart] = useState("");
  const [customEnd, setCustomEnd] = useState("");

  const label = formatDateRangeLabel(selectedPreset, customRange);

  const handlePresetClick = (presetValue: string) => {
    onPresetChange(presetValue);
    setIsCustomMode(false);
    setIsOpen(false);
  };

  const handleCustomApply = () => {
    if (customStart && customEnd && customStart <= customEnd) {
      onCustomRangeChange({ startDate: customStart, endDate: customEnd });
      setIsOpen(false);
      setIsCustomMode(false);
    }
  };

  const handleOpenCustom = () => {
    // Pre-fill with current custom range if one exists
    if (customRange) {
      setCustomStart(customRange.startDate);
      setCustomEnd(customRange.endDate);
    } else {
      setCustomStart("");
      setCustomEnd("");
    }
    setIsCustomMode(true);
  };

  const isCustomActive = customRange !== null;

  return (
    <div className="relative">
      <Button
        variant="outline"
        size="sm"
        className="gap-2"
        onClick={() => {
          setIsOpen(!isOpen);
          if (!isOpen) setIsCustomMode(false);
        }}
      >
        <Calendar className="h-4 w-4" />
        {label}
        <ChevronDown
          className={cn(
            "h-3 w-3 transition-transform",
            isOpen && "rotate-180"
          )}
        />
      </Button>

      {isOpen && (
        <>
          {/* Backdrop to close dropdown */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => {
              setIsOpen(false);
              setIsCustomMode(false);
            }}
          />

          {/* Dropdown menu */}
          <div className="absolute right-0 top-full mt-1 z-50 w-72 rounded-md border bg-popover shadow-md">
            {/* Preset options */}
            <div className="p-1">
              {DATE_PRESETS.map((preset) => {
                const isActive =
                  !isCustomActive && selectedPreset === preset.value;
                return (
                  <button
                    key={preset.value}
                    className={cn(
                      "flex w-full items-center justify-between rounded-sm px-3 py-2 text-sm hover:bg-accent hover:text-accent-foreground",
                      isActive && "bg-accent"
                    )}
                    onClick={() => handlePresetClick(preset.value)}
                  >
                    <span>{preset.label}</span>
                    {isActive && <Check className="h-4 w-4 text-primary" />}
                  </button>
                );
              })}
            </div>

            {/* Divider */}
            <div className="border-t mx-1" />

            {/* Custom Range */}
            <div className="p-1">
              {!isCustomMode ? (
                <button
                  className={cn(
                    "flex w-full items-center justify-between rounded-sm px-3 py-2 text-sm hover:bg-accent hover:text-accent-foreground",
                    isCustomActive && "bg-accent"
                  )}
                  onClick={handleOpenCustom}
                >
                  <span>Custom Range</span>
                  {isCustomActive && (
                    <Check className="h-4 w-4 text-primary" />
                  )}
                </button>
              ) : (
                <div className="px-3 py-2 space-y-3">
                  <p className="text-sm font-medium text-muted-foreground">
                    Custom Range
                  </p>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-xs text-muted-foreground mb-1 block">
                        Start Date
                      </label>
                      <input
                        type="date"
                        value={customStart}
                        onChange={(e) => setCustomStart(e.target.value)}
                        className="w-full rounded-md border bg-background px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-muted-foreground mb-1 block">
                        End Date
                      </label>
                      <input
                        type="date"
                        value={customEnd}
                        onChange={(e) => setCustomEnd(e.target.value)}
                        className="w-full rounded-md border bg-background px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                      />
                    </div>
                  </div>
                  {customStart && customEnd && customStart > customEnd && (
                    <p className="text-xs text-red-500">
                      Start date must be before end date
                    </p>
                  )}
                  <Button
                    size="sm"
                    className="w-full"
                    disabled={
                      !customStart || !customEnd || customStart > customEnd
                    }
                    onClick={handleCustomApply}
                  >
                    Apply
                  </Button>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// Helper for conditional classes
function cn(...classes: (string | boolean | undefined)[]) {
  return classes.filter(Boolean).join(" ");
}
