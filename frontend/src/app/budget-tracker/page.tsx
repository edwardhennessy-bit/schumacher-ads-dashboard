"use client";

import { useState, useCallback } from "react";
import { Header } from "@/components/layout/Header";
import { BudgetTracker } from "@/components/dashboard/BudgetTracker";
import { DateRange, DEFAULT_PRESET, getPresetByValue } from "@/lib/date-range";

export default function BudgetTrackerPage() {
  const [selectedPreset, setSelectedPreset] = useState(DEFAULT_PRESET);
  const [customRange, setCustomRange] = useState<DateRange | null>(null);

  const getActiveDateRange = useCallback((): DateRange => {
    if (customRange) return customRange;
    const preset = getPresetByValue(selectedPreset);
    return preset ? preset.getRange() : getPresetByValue(DEFAULT_PRESET)!.getRange();
  }, [customRange, selectedPreset]);

  const range = getActiveDateRange();

  return (
    <div className="min-h-screen bg-background">
      <Header
        title="Budget Tracker"
        subtitle="Monthly Budget vs. Actual Spend · TOF / MOF / BOF Breakdown"
        selectedPreset={selectedPreset}
        customRange={customRange}
        onPresetChange={(p) => { setSelectedPreset(p); setCustomRange(null); }}
        onCustomRangeChange={setCustomRange}
      />
      <div className="p-6">
        <BudgetTracker startDate={range.startDate} endDate={range.endDate} />
      </div>
    </div>
  );
}
