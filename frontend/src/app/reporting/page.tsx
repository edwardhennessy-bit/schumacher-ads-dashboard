"use client";

import { useState, useCallback } from "react";
import { Header } from "@/components/layout/Header";
import {
  FileText,
  Copy,
  Check,
  Sparkles,
  RefreshCw,
  DollarSign,
  UserPlus,
  Target,
  Monitor,
} from "lucide-react";
import { api } from "@/lib/api";
import { formatCurrency, formatNumber } from "@/lib/mock-data";
import {
  DateRange,
  DEFAULT_PRESET,
  getPresetByValue,
} from "@/lib/date-range";

export default function ReportingPage() {
  const [selectedPreset, setSelectedPreset] = useState(DEFAULT_PRESET);
  const [customRange, setCustomRange] = useState<DateRange | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [copied, setCopied] = useState(false);
  const [result, setResult] = useState<{
    text: string;
    period_label: string;
    meta_spend: number;
    google_spend: number;
    microsoft_spend: number;
    total_spend: number;
    google_leads: number;
    google_opportunities: number;
    google_lead_to_opp_pct: number;
    meta_leads: number;
    meta_remarketing_cpa: number;
    meta_prospecting_cpa: number;
    bing_cpa: number;
    bing_leads: number;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const getActiveDateRange = useCallback((): DateRange => {
    if (customRange) return customRange;
    const preset = getPresetByValue(selectedPreset);
    return preset ? preset.getRange() : getPresetByValue(DEFAULT_PRESET)!.getRange();
  }, [customRange, selectedPreset]);

  const handleGenerate = async () => {
    if (isGenerating) return;
    setIsGenerating(true);
    setError(null);
    setResult(null);

    const dr = getActiveDateRange();
    try {
      const data = await api.generateWeeklyKpiSection(dr.startDate, dr.endDate);
      setResult(data);
    } catch (err) {
      setError(`Failed to generate report: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCopy = async () => {
    if (!result?.text) return;
    try {
      await navigator.clipboard.writeText(result.text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      // fallback — select the textarea
    }
  };

  const handlePresetChange = (preset: string) => {
    setSelectedPreset(preset);
    setCustomRange(null);
  };

  return (
    <div className="min-h-screen bg-background">
      <Header
        title="Reporting"
        subtitle="Weekly KPI Section Generator"
        onRefresh={result ? handleGenerate : undefined}
        isLoading={isGenerating}
        selectedPreset={selectedPreset}
        customRange={customRange}
        onPresetChange={handlePresetChange}
        onCustomRangeChange={setCustomRange}
      />

      <div className="p-6 space-y-6 max-w-5xl">
        {/* Intro card */}
        <div className="rounded-lg border bg-card p-5 flex items-start gap-4">
          <div className="rounded-full bg-primary/10 p-3">
            <FileText className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h2 className="font-semibold text-base mb-1">Weekly Agenda — Performance Metrics &amp; KPIs</h2>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Select your reporting period using the date range picker above, then click{" "}
              <strong>Generate KPI Section</strong>. The output matches your standard weekly agenda
              template with live data pulled from Meta, Google Ads, and Microsoft Ads. Copy it
              directly into your Google Doc.
            </p>
          </div>
        </div>

        {/* Generate button */}
        <button
          onClick={handleGenerate}
          disabled={isGenerating}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-lg font-medium text-sm transition-all
            ${isGenerating
              ? "bg-gray-100 text-gray-400 cursor-not-allowed border border-gray-200"
              : "bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm"
            }`}
        >
          {isGenerating ? (
            <>
              <RefreshCw className="h-4 w-4 animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <Sparkles className="h-4 w-4" />
              Generate KPI Section
            </>
          )}
        </button>

        {/* Error state */}
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Results */}
        {result && (
          <div className="space-y-5">
            {/* Metric snapshot cards */}
            <div>
              <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
                Period: {result.period_label}
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="rounded-lg border bg-card p-4">
                  <div className="flex items-center gap-2 text-muted-foreground text-xs mb-1">
                    <DollarSign className="h-3.5 w-3.5" /> Total Spend
                  </div>
                  <p className="text-xl font-bold">{formatCurrency(result.total_spend)}</p>
                  <div className="mt-2 space-y-0.5 text-xs text-muted-foreground">
                    <p>Google: {formatCurrency(result.google_spend)}</p>
                    <p>Meta: {formatCurrency(result.meta_spend)}</p>
                    <p>Bing: {formatCurrency(result.microsoft_spend)}</p>
                  </div>
                </div>

                <div className="rounded-lg border bg-card p-4">
                  <div className="flex items-center gap-2 text-muted-foreground text-xs mb-1">
                    <UserPlus className="h-3.5 w-3.5" /> Google Leads
                  </div>
                  <p className="text-xl font-bold">{formatNumber(result.google_leads)}</p>
                  <p className="mt-2 text-xs text-muted-foreground">
                    Target: &gt;950/month
                  </p>
                  <p className="text-xs text-muted-foreground">
                    L→Opp: {result.google_lead_to_opp_pct.toFixed(1)}% (target ≥10%)
                  </p>
                </div>

                <div className="rounded-lg border bg-card p-4">
                  <div className="flex items-center gap-2 text-muted-foreground text-xs mb-1">
                    <Target className="h-3.5 w-3.5" /> Meta Leads
                  </div>
                  <p className="text-xl font-bold">{formatNumber(result.meta_leads)}</p>
                  <div className="mt-2 space-y-0.5 text-xs text-muted-foreground">
                    <p>Remarketing CPA: {formatCurrency(result.meta_remarketing_cpa)}</p>
                    <p>Prospecting CPA: {formatCurrency(result.meta_prospecting_cpa)}</p>
                  </div>
                </div>

                <div className="rounded-lg border bg-card p-4">
                  <div className="flex items-center gap-2 text-muted-foreground text-xs mb-1">
                    <Monitor className="h-3.5 w-3.5" /> Bing Leads
                  </div>
                  <p className="text-xl font-bold">{formatNumber(result.bing_leads)}</p>
                  <div className="mt-2 space-y-0.5 text-xs text-muted-foreground">
                    <p>CPA: {formatCurrency(result.bing_cpa)}</p>
                    <p>Target: &lt;$55 CPA</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Copy-paste text block */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-semibold">Copy-Paste Block</h3>
                <button
                  onClick={handleCopy}
                  className={`flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-md border transition-all
                    ${copied
                      ? "bg-green-50 text-green-700 border-green-200"
                      : "bg-white text-gray-700 border-gray-200 hover:bg-gray-50 hover:border-gray-300"
                    }`}
                >
                  {copied ? (
                    <>
                      <Check className="h-3.5 w-3.5" /> Copied!
                    </>
                  ) : (
                    <>
                      <Copy className="h-3.5 w-3.5" /> Copy to Clipboard
                    </>
                  )}
                </button>
              </div>
              <textarea
                readOnly
                value={result.text}
                onClick={(e) => (e.target as HTMLTextAreaElement).select()}
                className="w-full h-96 rounded-lg border border-gray-200 bg-gray-50 p-4 font-mono text-xs text-gray-800 resize-none focus:outline-none focus:ring-2 focus:ring-primary/30"
              />
              <p className="text-xs text-muted-foreground mt-1.5">
                Click inside the box to select all, or use the Copy button above.
              </p>
            </div>
          </div>
        )}

        {/* Empty state */}
        {!result && !isGenerating && !error && (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="rounded-full bg-muted p-6 mb-4">
              <FileText className="h-10 w-10 text-muted-foreground" />
            </div>
            <h3 className="text-lg font-semibold mb-2">Ready to Generate</h3>
            <p className="text-sm text-muted-foreground max-w-md">
              Select your reporting period (default is MTD) and click{" "}
              <strong>Generate KPI Section</strong> to pull live data from all platforms and
              produce the formatted text block for your weekly agenda doc.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
