"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Header } from "@/components/layout/Header";
import {
  Receipt,
  Sparkles,
  RefreshCw,
  ExternalLink,
  CheckCircle2,
  XCircle,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { api } from "@/lib/api";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getPriorMonthLabel(): string {
  const now = new Date();
  const prior = new Date(now.getFullYear(), now.getMonth() - 1, 1);
  return prior.toLocaleString("en-US", { month: "long", year: "numeric" });
}

function parseCurrency(raw: string): number {
  return parseFloat(raw.replace(/[$,]/g, "")) || 0;
}

function formatCurrencyInput(val: string): string {
  // Strip non-numeric characters except dot, then reformat
  const numeric = val.replace(/[^0-9.]/g, "");
  return numeric;
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type JobStatus = "idle" | "queued" | "running" | "done" | "error";

interface JobState {
  jobId: string;
  status: JobStatus;
  logs: string;
  url: string | null;
  error: string | null;
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function SpendReportPage() {
  // Form inputs
  const [googleVal,    setGoogleVal]    = useState("");
  const [microsoftVal, setMicrosoftVal] = useState("");
  const [metaVal,      setMetaVal]      = useState("");
  const [monthOverride, setMonthOverride] = useState("");

  // Job state
  const [job, setJob] = useState<JobState | null>(null);
  const [logsOpen, setLogsOpen] = useState(true);

  const logRef = useRef<HTMLPreElement>(null);
  const pollRef = useRef<NodeJS.Timeout | null>(null);

  const priorMonth = getPriorMonthLabel();
  const reportMonth = monthOverride.trim() || priorMonth;

  // Auto-scroll logs to bottom
  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [job?.logs]);

  // Stop polling when done or errored
  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  // Start polling job status
  const startPolling = useCallback((jobId: string) => {
    stopPolling();
    pollRef.current = setInterval(async () => {
      try {
        const data = await api.getSpendReportStatus(jobId);
        setJob(prev => prev ? {
          ...prev,
          status: data.status as JobStatus,
          logs:   data.logs,
          url:    data.url,
          error:  data.error,
        } : prev);

        if (data.status === "done" || data.status === "error" || data.status === "not_found") {
          stopPolling();
        }
      } catch {
        // Keep polling on transient network errors
      }
    }, 2000);
  }, [stopPolling]);

  // Cleanup on unmount
  useEffect(() => () => stopPolling(), [stopPolling]);

  const canGenerate =
    parseCurrency(googleVal) > 0 &&
    parseCurrency(microsoftVal) > 0 &&
    parseCurrency(metaVal) > 0 &&
    (!job || job.status === "done" || job.status === "error");

  const isRunning = job?.status === "queued" || job?.status === "running";

  const handleGenerate = async () => {
    if (!canGenerate || isRunning) return;

    setJob({ jobId: "", status: "queued", logs: "", url: null, error: null });
    setLogsOpen(true);

    try {
      const { job_id } = await api.generateSpendReport({
        googleHubspot:    parseCurrency(googleVal),
        microsoftHubspot: parseCurrency(microsoftVal),
        metaHubspot:      parseCurrency(metaVal),
        month:            monthOverride.trim() || undefined,
      });

      setJob({ jobId: job_id, status: "queued", logs: "", url: null, error: null });
      startPolling(job_id);
    } catch (err) {
      setJob({
        jobId: "",
        status: "error",
        logs: "",
        url: null,
        error: err instanceof Error ? err.message : String(err),
      });
    }
  };

  const handleReset = () => {
    stopPolling();
    setJob(null);
    setGoogleVal("");
    setMicrosoftVal("");
    setMetaVal("");
    setMonthOverride("");
  };

  // Extract current turn from logs
  const currentTurn = (() => {
    if (!job?.logs) return null;
    const matches = [...job.logs.matchAll(/\[Turn (\d+)\]/g)];
    return matches.length ? parseInt(matches[matches.length - 1][1]) : null;
  })();

  const fetchingDone = job?.logs.includes("Starting agent...");
  const uploadingDone = job?.logs.includes("[Upload]");

  return (
    <div className="min-h-screen bg-background">
      <Header
        title="Spend Report"
        subtitle="Monthly Schumacher Homes Spend by Location"
      />

      <div className="p-6 space-y-6 max-w-3xl">

        {/* ── Intro card ── */}
        <div className="rounded-lg border bg-card p-5 flex items-start gap-4">
          <div className="rounded-full bg-primary/10 p-3 shrink-0">
            <Receipt className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h2 className="font-semibold text-base mb-1">Auto-Generated Spend Workbook</h2>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Enter the three HubSpot invoice totals below and click{" "}
              <strong>Generate Report</strong>. The agent will automatically pull spend
              data from Google Ads, Microsoft Ads, and Meta for{" "}
              <strong>{reportMonth}</strong>, allocate it across all 32 locations,
              reconcile against your invoice figures, and deliver a ready-to-share
              Google Sheet link.
            </p>
          </div>
        </div>

        {/* ── Form ── */}
        {(!job || job.status === "error") && (
          <div className="rounded-lg border bg-card p-6 space-y-6">
            <div>
              <h3 className="font-semibold mb-1">HubSpot Invoice Totals</h3>
              <p className="text-xs text-muted-foreground mb-4">
                Enter the exact invoice amounts from HubSpot for each platform.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {/* Google */}
                <div>
                  <label className="block text-sm font-medium mb-1.5">
                    Google Ads
                  </label>
                  <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">$</span>
                    <input
                      type="text"
                      inputMode="decimal"
                      placeholder="0.00"
                      value={googleVal}
                      onChange={e => setGoogleVal(formatCurrencyInput(e.target.value))}
                      className="w-full rounded-md border bg-background pl-7 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                    />
                  </div>
                </div>

                {/* Microsoft */}
                <div>
                  <label className="block text-sm font-medium mb-1.5">
                    Microsoft / Bing
                  </label>
                  <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">$</span>
                    <input
                      type="text"
                      inputMode="decimal"
                      placeholder="0.00"
                      value={microsoftVal}
                      onChange={e => setMicrosoftVal(formatCurrencyInput(e.target.value))}
                      className="w-full rounded-md border bg-background pl-7 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                    />
                  </div>
                </div>

                {/* Meta */}
                <div>
                  <label className="block text-sm font-medium mb-1.5">
                    Meta (FB / IG)
                  </label>
                  <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">$</span>
                    <input
                      type="text"
                      inputMode="decimal"
                      placeholder="0.00"
                      value={metaVal}
                      onChange={e => setMetaVal(formatCurrencyInput(e.target.value))}
                      className="w-full rounded-md border bg-background pl-7 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Month override */}
            <div>
              <label className="block text-sm font-medium mb-1.5">
                Report Month{" "}
                <span className="text-muted-foreground font-normal">(optional — defaults to prior month)</span>
              </label>
              <input
                type="text"
                placeholder={`e.g. ${priorMonth}`}
                value={monthOverride}
                onChange={e => setMonthOverride(e.target.value)}
                className="w-full sm:w-64 rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
              />
            </div>

            {/* Error from previous run */}
            {job?.status === "error" && (
              <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 flex items-start gap-2 text-sm text-red-700">
                <XCircle className="h-4 w-4 shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium">Report generation failed</p>
                  {job.error && <p className="mt-0.5 text-xs">{job.error}</p>}
                </div>
              </div>
            )}

            {/* Generate button */}
            <button
              onClick={handleGenerate}
              disabled={!canGenerate}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-lg font-medium text-sm transition-all
                ${canGenerate
                  ? "bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm"
                  : "bg-muted text-muted-foreground cursor-not-allowed"
                }`}
            >
              <Sparkles className="h-4 w-4" />
              Generate Report for {reportMonth}
            </button>
          </div>
        )}

        {/* ── Progress ── */}
        {job && (job.status === "queued" || job.status === "running") && (
          <div className="rounded-lg border bg-card p-6 space-y-4">
            {/* Status row */}
            <div className="flex items-center gap-3">
              <RefreshCw className="h-5 w-5 animate-spin text-primary" />
              <div>
                <p className="font-semibold text-sm">
                  {job.status === "queued" ? "Starting up…" : (
                    uploadingDone ? "Uploading to Google Sheets…" :
                    fetchingDone  ? `Generating workbook${currentTurn ? ` — Turn ${currentTurn}` : "…"}` :
                    "Fetching platform data…"
                  )}
                </p>
                <p className="text-xs text-muted-foreground">This takes 2–3 minutes</p>
              </div>
            </div>

            {/* Progress steps */}
            <div className="flex items-center gap-2 text-xs">
              {[
                { label: "Fetch data",  done: fetchingDone },
                { label: "Build workbook", done: uploadingDone },
                { label: "Upload Sheet", done: job.status === "done" },
              ].map((step, i) => (
                <div key={i} className="flex items-center gap-1">
                  {i > 0 && <span className="text-muted-foreground mx-1">→</span>}
                  <span className={step.done ? "text-green-600 font-medium" : "text-muted-foreground"}>
                    {step.done ? "✓ " : ""}{step.label}
                  </span>
                </div>
              ))}
            </div>

            {/* Live logs */}
            <div>
              <button
                onClick={() => setLogsOpen(o => !o)}
                className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground mb-2 transition-colors"
              >
                {logsOpen ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                {logsOpen ? "Hide" : "Show"} live output
              </button>
              {logsOpen && (
                <pre
                  ref={logRef}
                  className="h-64 overflow-y-auto rounded-md bg-black/80 p-3 text-xs text-green-300 font-mono leading-relaxed whitespace-pre-wrap"
                >
                  {job.logs || "Waiting for output…"}
                </pre>
              )}
            </div>
          </div>
        )}

        {/* ── Success ── */}
        {job?.status === "done" && (
          <div className="rounded-lg border border-green-200 bg-card p-6 space-y-5">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="h-6 w-6 text-green-500 shrink-0" />
              <div>
                <p className="font-semibold">Report Ready — {reportMonth}</p>
                <p className="text-sm text-muted-foreground">
                  Google Sheet generated and shared. Send the link directly to the client.
                </p>
              </div>
            </div>

            {job.url && (
              <a
                href={job.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-center gap-2 w-full rounded-lg bg-primary text-primary-foreground py-3 font-semibold text-sm hover:bg-primary/90 transition-colors shadow-sm"
              >
                <ExternalLink className="h-4 w-4" />
                Open Google Sheet
              </a>
            )}

            {job.url && (
              <div className="rounded-md bg-muted px-3 py-2">
                <p className="text-xs text-muted-foreground mb-1 font-medium">Shareable link</p>
                <p className="text-xs font-mono break-all text-foreground">{job.url}</p>
              </div>
            )}

            {/* Collapsible logs */}
            <div>
              <button
                onClick={() => setLogsOpen(o => !o)}
                className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
              >
                {logsOpen ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                {logsOpen ? "Hide" : "View"} full agent log
              </button>
              {logsOpen && (
                <pre className="mt-2 h-48 overflow-y-auto rounded-md bg-black/80 p-3 text-xs text-green-300 font-mono leading-relaxed whitespace-pre-wrap">
                  {job.logs}
                </pre>
              )}
            </div>

            <button
              onClick={handleReset}
              className="text-sm text-muted-foreground hover:text-foreground underline underline-offset-2 transition-colors"
            >
              Generate another report
            </button>
          </div>
        )}

        {/* ── Error (standalone, no form shown) ── */}
        {job?.status === "error" && !job.logs && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-4 flex items-start gap-3">
            <XCircle className="h-5 w-5 text-red-500 shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-red-800 text-sm">Generation failed</p>
              {job.error && <p className="mt-1 text-xs text-red-700">{job.error}</p>}
              <button onClick={handleReset} className="mt-3 text-xs text-red-600 underline">
                Try again
              </button>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
