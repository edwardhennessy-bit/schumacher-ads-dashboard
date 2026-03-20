"use client";

import { useState, useCallback, useRef } from "react";
import {
  ChevronRight,
  ChevronLeft,
  Sparkles,
  RefreshCw,
  Plus,
  Trash2,
  CheckCircle,
  Circle,
  Download,
  Upload,
  FileText,
  X,
  Globe,
} from "lucide-react";
import { SlidePreview } from "./SlidePreview";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8003";

// ── Types ───────────────────────────────────────────────────────────────────

interface LocationRow {
  location: string;
  leads: number;
  visits: number;
  cpl: number;
  quotes: number;
  spend: number;
}

interface AttributionAnswers {
  google_sync_status: string;
  meta_sync_status: string;
  microsoft_sync_status: string;
  pmax_status: string;
  meta_pixel_status: string;
  lead_scoring_status: string;
  hubspot_leads: number;
  platform_leads: number;
  hubspot_quotes: number;
  platform_quotes: number;
  action_items: string;
}

interface SlideContent {
  slide_number: number;
  title: string;
  content: Record<string, unknown>;
}

interface MonthlySlidesResponse {
  report_month: string;
  period_label: string;
  slides: SlideContent[];
}

// ── Step definitions ────────────────────────────────────────────────────────
const STEPS = [
  { id: 1, label: "Period", shortLabel: "Period" },
  { id: 2, label: "Platform KPIs", shortLabel: "KPIs" },
  { id: 3, label: "HubSpot Data", shortLabel: "HubSpot" },
  { id: 4, label: "Attribution", shortLabel: "Attribution" },
  { id: 5, label: "Creatives", shortLabel: "Creatives" },
  { id: 6, label: "Initiatives", shortLabel: "Initiatives" },
  { id: 7, label: "Generate", shortLabel: "Generate" },
];

// ── Helpers ─────────────────────────────────────────────────────────────────

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

function monthStartEnd(year: number, month: number): { start: string; end: string } {
  const start = new Date(year, month - 1, 1);
  const end = new Date(year, month, 0); // last day
  const pad = (n: number) => String(n).padStart(2, "0");
  return {
    start: `${year}-${pad(month)}-01`,
    end: `${year}-${pad(month)}-${pad(end.getDate())}`,
  };
}

function emptyLocation(): LocationRow {
  return { location: "", leads: 0, visits: 0, cpl: 0, quotes: 0, spend: 0 };
}

// ── Step indicator ──────────────────────────────────────────────────────────
function StepBar({ current }: { current: number }) {
  return (
    <div className="flex items-center gap-1 mb-8 overflow-x-auto pb-1">
      {STEPS.map((step, i) => {
        const done = current > step.id;
        const active = current === step.id;
        return (
          <div key={step.id} className="flex items-center">
            <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-all ${
              active ? "bg-[#1a2744] text-white shadow" :
              done ? "bg-green-100 text-green-700" :
              "bg-gray-100 text-gray-400"
            }`}>
              {done ? <CheckCircle className="h-3 w-3" /> : <Circle className="h-3 w-3" />}
              {step.shortLabel}
            </div>
            {i < STEPS.length - 1 && (
              <div className={`h-px w-4 mx-1 ${done ? "bg-green-300" : "bg-gray-200"}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Step 1: Period ──────────────────────────────────────────────────────────
function Step1({
  year, month, onYearChange, onMonthChange, onNext,
}: {
  year: number; month: number;
  onYearChange: (y: number) => void;
  onMonthChange: (m: number) => void;
  onNext: () => void;
}) {
  const currentYear = new Date().getFullYear();
  const years = [currentYear - 1, currentYear, currentYear + 1];
  return (
    <div className="space-y-6 max-w-md">
      <div>
        <h3 className="text-base font-semibold mb-1">Select Reporting Period</h3>
        <p className="text-sm text-muted-foreground">
          Choose the month and year for the performance report.
        </p>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="text-xs font-medium text-gray-600 block mb-1">Month</label>
          <select
            value={month}
            onChange={(e) => onMonthChange(Number(e.target.value))}
            className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1a2744]/30"
          >
            {MONTHS.map((m, i) => (
              <option key={m} value={i + 1}>{m}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs font-medium text-gray-600 block mb-1">Year</label>
          <select
            value={year}
            onChange={(e) => onYearChange(Number(e.target.value))}
            className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1a2744]/30"
          >
            {years.map((y) => <option key={y} value={y}>{y}</option>)}
          </select>
        </div>
      </div>
      <div className="rounded-lg bg-blue-50 border border-blue-100 px-4 py-3 text-sm text-blue-800">
        Report period: <strong>{MONTHS[month - 1]} {year}</strong>
        &nbsp;({monthStartEnd(year, month).start} → {monthStartEnd(year, month).end})
      </div>
      <button
        onClick={onNext}
        className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#1a2744] text-white font-medium text-sm hover:bg-[#1a2744]/90"
      >
        Continue <ChevronRight className="h-4 w-4" />
      </button>
    </div>
  );
}

// ── Step 2: Platform KPIs (informational, data fetched at generate time) ────
function Step2({ year, month, onNext, onBack }: {
  year: number; month: number; onNext: () => void; onBack: () => void;
}) {
  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h3 className="text-base font-semibold mb-1">Platform KPIs — Slide 2</h3>
        <p className="text-sm text-muted-foreground">
          Live data for <strong>{MONTHS[month - 1]} {year}</strong> will be fetched automatically from Meta, Google Ads, and Microsoft Ads when you generate the report. JARVIS will compare it against the previous month and write key takeaways.
        </p>
      </div>
      <div className="rounded-xl border border-[#1a2744]/20 bg-[#1a2744]/3 p-5">
        <h4 className="text-sm font-semibold text-[#1a2744] mb-3">What JARVIS will auto-populate:</h4>
        <ul className="space-y-2 text-sm text-gray-700">
          {[
            "Google Ads: Spend, Leads, CPL — vs. prior month",
            "Meta Ads: Spend, Leads, Remarketing CPL, Prospecting CPL — vs. prior month",
            "Microsoft Ads: Spend, Leads, CPL — vs. prior month",
            "Total spend + blended CPL across all platforms",
            "AI-written key takeaways & next steps",
          ].map((item) => (
            <li key={item} className="flex items-start gap-2">
              <CheckCircle className="h-4 w-4 text-green-500 flex-shrink-0 mt-0.5" />
              {item}
            </li>
          ))}
        </ul>
      </div>
      <div className="rounded-lg bg-amber-50 border border-amber-100 px-4 py-3 text-sm text-amber-800">
        <strong>Optional:</strong> You can add custom key takeaways or next steps on the final slide preview if you want to override JARVIS&apos;s generated text.
      </div>
      <NavButtons onBack={onBack} onNext={onNext} />
    </div>
  );
}

// ── Step 3: HubSpot Location Data ───────────────────────────────────────────
function Step3({
  locations,
  onLocationsChange,
  keyInsights,
  onKeyInsightsChange,
  focusAreas,
  onFocusAreasChange,
  onNext,
  onBack,
}: {
  locations: LocationRow[];
  onLocationsChange: (rows: LocationRow[]) => void;
  keyInsights: string;
  onKeyInsightsChange: (v: string) => void;
  focusAreas: string;
  onFocusAreasChange: (v: string) => void;
  onNext: () => void;
  onBack: () => void;
}) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [uploadedFile, setUploadedFile] = useState("");

  const updateRow = (i: number, field: keyof LocationRow, value: string | number) => {
    const updated = [...locations];
    (updated[i] as unknown as Record<string, unknown>)[field] = value;
    onLocationsChange(updated);
  };

  const addRow = () => onLocationsChange([...locations, emptyLocation()]);

  const removeRow = (i: number) => {
    const updated = [...locations];
    updated.splice(i, 1);
    onLocationsChange(updated);
  };

  const pasteHandler = (e: React.ClipboardEvent) => {
    const text = e.clipboardData.getData("text");
    const rows = text.trim().split("\n").map((line) => {
      const [location, leads, visits, cpl, quotes, spend] = line.split("\t");
      return {
        location: location?.trim() || "",
        leads: parseInt(leads) || 0,
        visits: parseInt(visits) || 0,
        cpl: parseFloat(cpl?.replace(/[$,]/g, "")) || 0,
        quotes: parseInt(quotes) || 0,
        spend: parseFloat(spend?.replace(/[$,]/g, "")) || 0,
      };
    }).filter((r) => r.location);
    if (rows.length > 1) {
      e.preventDefault();
      onLocationsChange(rows);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setUploadError("");
    setUploadedFile("");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API_BASE}/api/reports/parse-scorecard`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || res.statusText);
      }
      const data = await res.json();
      const rows: LocationRow[] = (data.locations || []).map((l: Partial<LocationRow>) => ({
        location: l.location || "",
        leads: l.leads || 0,
        visits: l.visits || 0,
        cpl: l.cpl || 0,
        quotes: l.quotes || 0,
        spend: l.spend || 0,
      }));
      if (rows.length > 0) onLocationsChange(rows);
      if (data.key_insights) onKeyInsightsChange(data.key_insights);
      if (data.focus_areas) onFocusAreasChange(data.focus_areas);
      setUploadedFile(file.name);
    } catch (err) {
      setUploadError(String(err instanceof Error ? err.message : err));
    } finally {
      setUploading(false);
      // reset so the same file can be re-uploaded
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h3 className="text-base font-semibold mb-1">Design Center Scorecard — Slide 3</h3>
        <p className="text-sm text-muted-foreground">
          Upload a report file or paste directly from a spreadsheet. JARVIS will auto-populate the table from CSV, Excel, PDF, or a screenshot.
        </p>
      </div>

      {/* Upload zone */}
      <div className="rounded-xl border-2 border-dashed border-[#1a2744]/25 bg-[#1a2744]/3 p-5">
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
          <div className="flex-1">
            <p className="text-sm font-medium text-gray-700 mb-0.5">Auto-populate from file</p>
            <p className="text-xs text-muted-foreground">
              Upload your HubSpot export or report screenshot — JARVIS will extract location data automatically.
              Accepts <strong>CSV, XLSX, PDF, PNG, JPG</strong>.
            </p>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            {uploadedFile && (
              <div className="flex items-center gap-1.5 text-xs font-medium text-green-700 bg-green-50 border border-green-200 px-2.5 py-1.5 rounded-lg">
                <FileText className="h-3.5 w-3.5" />
                {uploadedFile}
                <button onClick={() => setUploadedFile("")} className="ml-0.5 text-green-500 hover:text-green-700">
                  <X className="h-3 w-3" />
                </button>
              </div>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.tsv,.xlsx,.xls,.pdf,.png,.jpg,.jpeg,.webp"
              className="hidden"
              onChange={handleFileUpload}
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm transition-all ${
                uploading
                  ? "bg-gray-100 text-gray-400 cursor-not-allowed border border-gray-200"
                  : "bg-[#1a2744] text-white hover:bg-[#1a2744]/90 shadow-sm"
              }`}
            >
              {uploading ? (
                <><RefreshCw className="h-4 w-4 animate-spin" /> Analyzing file...</>
              ) : (
                <><Upload className="h-4 w-4" /> Upload & Auto-Fill</>
              )}
            </button>
          </div>
        </div>

        {uploadError && (
          <div className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
            {uploadError}
          </div>
        )}
      </div>

      {/* Location table */}
      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-[#1a2744] text-white">
              {["Location", "Leads", "Visits", "CPL ($)", "Quotes", "Spend ($)", ""].map((h) => (
                <th key={h} className="px-3 py-2.5 text-left font-semibold text-xs">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody onPaste={pasteHandler}>
            {locations.map((row, i) => (
              <tr key={i} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="px-2 py-1">
                  <input
                    className="w-full rounded border-0 bg-transparent px-1 py-0.5 text-sm focus:outline-none focus:ring-1 focus:ring-[#1a2744]/30"
                    value={row.location}
                    placeholder="Location name"
                    onChange={(e) => updateRow(i, "location", e.target.value)}
                  />
                </td>
                {(["leads", "visits", "cpl", "quotes", "spend"] as (keyof LocationRow)[]).map((field) => (
                  <td key={field} className="px-2 py-1">
                    <input
                      type="number"
                      className="w-full rounded border-0 bg-transparent px-1 py-0.5 text-sm text-right focus:outline-none focus:ring-1 focus:ring-[#1a2744]/30"
                      value={row[field] || ""}
                      onChange={(e) => updateRow(i, field, field === "cpl" || field === "spend" ? parseFloat(e.target.value) || 0 : parseInt(e.target.value) || 0)}
                    />
                  </td>
                ))}
                <td className="px-2 py-1">
                  <button onClick={() => removeRow(i)} className="text-gray-300 hover:text-red-400">
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <button
        onClick={addRow}
        className="flex items-center gap-1.5 text-xs font-medium text-[#1a2744] border border-[#1a2744]/30 px-3 py-1.5 rounded-lg hover:bg-[#1a2744]/5"
      >
        <Plus className="h-3.5 w-3.5" /> Add Location
      </button>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="text-xs font-medium text-gray-600 block mb-1">
            Key Insights <span className="text-gray-400">(optional — JARVIS will generate if blank)</span>
          </label>
          <textarea
            rows={4}
            value={keyInsights}
            onChange={(e) => onKeyInsightsChange(e.target.value)}
            placeholder="- Akron-Canton leads all locations in volume at the lowest CPL&#10;- Nashville has highest spend but low conversion efficiency..."
            className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-[#1a2744]/30"
          />
        </div>
        <div>
          <label className="text-xs font-medium text-gray-600 block mb-1">Focus Areas <span className="text-gray-400">(optional)</span></label>
          <textarea
            rows={4}
            value={focusAreas}
            onChange={(e) => onFocusAreasChange(e.target.value)}
            placeholder="- Audit Nashville spend&#10;- Investigate Knoxville visit gap&#10;- Scale efficient markets"
            className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-[#1a2744]/30"
          />
        </div>
      </div>

      <NavButtons onBack={onBack} onNext={onNext} />
    </div>
  );
}

// ── Step 4: Attribution Q&A ─────────────────────────────────────────────────
const SYNC_OPTIONS = ["On Track", "In Progress", "Off Track", "N/A"];
const PIXEL_OPTIONS = ["Healthy", "Issues Detected", "Not Set Up"];

function Step4({
  answers,
  onAnswersChange,
  onNext,
  onBack,
}: {
  answers: AttributionAnswers;
  onAnswersChange: (a: AttributionAnswers) => void;
  onNext: () => void;
  onBack: () => void;
}) {
  const set = (field: keyof AttributionAnswers, value: string | number) => {
    onAnswersChange({ ...answers, [field]: value });
  };

  const SelectField = ({
    label,
    field,
    options,
  }: {
    label: string;
    field: keyof AttributionAnswers;
    options: string[];
  }) => (
    <div>
      <label className="text-xs font-medium text-gray-600 block mb-1">{label}</label>
      <select
        value={answers[field] as string}
        onChange={(e) => set(field, e.target.value)}
        className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1a2744]/30"
      >
        {options.map((o) => <option key={o}>{o}</option>)}
      </select>
    </div>
  );

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h3 className="text-base font-semibold mb-1">Attribution & Data Integrity — Slide 4</h3>
        <p className="text-sm text-muted-foreground">
          Answer a few quick questions so JARVIS can populate the attribution slide accurately.
        </p>
      </div>

      <div className="rounded-xl border p-5 space-y-4">
        <h4 className="text-sm font-semibold text-gray-700">HubSpot Sync Status</h4>
        <div className="grid grid-cols-3 gap-3">
          <SelectField label="Google Sync" field="google_sync_status" options={SYNC_OPTIONS} />
          <SelectField label="Meta Sync" field="meta_sync_status" options={SYNC_OPTIONS} />
          <SelectField label="Microsoft Sync" field="microsoft_sync_status" options={SYNC_OPTIONS} />
        </div>
      </div>

      <div className="rounded-xl border p-5 space-y-4">
        <h4 className="text-sm font-semibold text-gray-700">Platform vs HubSpot Lead Counts</h4>
        <div className="grid grid-cols-2 gap-4">
          {[
            { label: "Platform Leads (Meta + Google + Microsoft total)", field: "platform_leads" as const },
            { label: "HubSpot Leads", field: "hubspot_leads" as const },
            { label: "Platform Quotes / Opps", field: "platform_quotes" as const },
            { label: "HubSpot Quotes / Opps", field: "hubspot_quotes" as const },
          ].map((item) => (
            <div key={item.field}>
              <label className="text-xs font-medium text-gray-600 block mb-1">{item.label}</label>
              <input
                type="number"
                value={answers[item.field] || ""}
                onChange={(e) => set(item.field, parseInt(e.target.value) || 0)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1a2744]/30"
                placeholder="0"
              />
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-xl border p-5 space-y-4">
        <h4 className="text-sm font-semibold text-gray-700">Other Tracking Status</h4>
        <div className="grid grid-cols-2 gap-4">
          <SelectField label="Meta Pixel Health" field="meta_pixel_status" options={PIXEL_OPTIONS} />
          <SelectField label="Lead Scoring Status" field="lead_scoring_status" options={SYNC_OPTIONS} />
        </div>
        <div>
          <label className="text-xs font-medium text-gray-600 block mb-1">PMax Status & Notes</label>
          <input
            value={answers.pmax_status}
            onChange={(e) => set("pmax_status", e.target.value)}
            placeholder="e.g. Re-launched, exiting learning phase — lead volume increasing"
            className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1a2744]/30"
          />
        </div>
      </div>

      <div>
        <label className="text-xs font-medium text-gray-600 block mb-1">
          Action Items <span className="text-gray-400">(one per line)</span>
        </label>
        <textarea
          rows={4}
          value={answers.action_items}
          onChange={(e) => set("action_items", e.target.value)}
          placeholder="Close the quote attribution gap&#10;Continue monitoring PMax ramp&#10;Implement back end data integration for Meta visits"
          className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-[#1a2744]/30"
        />
      </div>

      <NavButtons onBack={onBack} onNext={onNext} />
    </div>
  );
}

// ── Step 5: Creative Preview ────────────────────────────────────────────────
function Step5({
  year, month, onNext, onBack,
}: {
  year: number; month: number; onNext: () => void; onBack: () => void;
}) {
  const [loading, setLoading] = useState(false);
  const [creatives, setCreatives] = useState<unknown[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState("");

  const { start, end } = monthStartEnd(year, month);

  const loadCreatives = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/api/reports/top-creatives?start_date=${start}&end_date=${end}&limit=6`);
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setCreatives(data);
      setLoaded(true);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [start, end]);

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h3 className="text-base font-semibold mb-1">Ad Development & Testing — Slide 5</h3>
        <p className="text-sm text-muted-foreground">
          JARVIS will pull the top Meta ad creatives by lead volume for <strong>{MONTHS[month - 1]} {year}</strong>, including their creative thumbnails and performance metrics.
        </p>
      </div>

      {!loaded && (
        <button
          onClick={loadCreatives}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 rounded-lg border border-[#1a2744]/30 text-sm font-medium text-[#1a2744] hover:bg-[#1a2744]/5 disabled:opacity-50"
        >
          {loading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
          {loading ? "Loading top creatives..." : "Load Top Creatives Preview"}
        </button>
      )}

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      )}

      {loaded && creatives.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {(creatives as Array<{ad_id: string; ad_name: string; campaign_name: string; leads: number; spend: number; cpl: number | null; ctr: number; thumbnail_url?: string; image_url?: string}>).map((c, i) => {
            const thumb = c.thumbnail_url || c.image_url;
            const proxyUrl = thumb ? `${API_BASE}/api/media/proxy?url=${encodeURIComponent(thumb)}` : null;
            return (
              <div key={c.ad_id} className="rounded-lg border overflow-hidden bg-white shadow-sm">
                <div className="relative h-32 bg-gray-100">
                  {proxyUrl ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={proxyUrl} alt={c.ad_name} className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-gray-300 text-3xl">🖼</div>
                  )}
                  <div className="absolute top-1.5 left-1.5 bg-[#1a2744] text-white text-xs px-1.5 py-0.5 rounded font-bold">
                    #{i + 1}
                  </div>
                </div>
                <div className="p-2.5">
                  <p className="text-xs font-medium line-clamp-2 mb-1">{c.ad_name}</p>
                  <div className="grid grid-cols-2 gap-x-2 text-xs text-gray-500">
                    <span>Leads: <strong className="text-gray-700">{c.leads}</strong></span>
                    <span>CPL: <strong className="text-gray-700">{c.cpl ? `$${c.cpl}` : "—"}</strong></span>
                    <span>Spend: <strong className="text-gray-700">${c.spend.toLocaleString()}</strong></span>
                    <span>CTR: <strong className="text-gray-700">{c.ctr}%</strong></span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {loaded && creatives.length === 0 && (
        <div className="rounded-lg bg-amber-50 border border-amber-100 px-4 py-3 text-sm text-amber-700">
          No creatives found for this period. The slide will be generated without thumbnails.
        </div>
      )}

      <div className="rounded-lg bg-blue-50 border border-blue-100 px-4 py-3 text-sm text-blue-800">
        Thumbnails are fetched live from Meta. If an image doesn&apos;t load, the ad&apos;s metrics will still appear in the report.
      </div>

      <NavButtons onBack={onBack} onNext={onNext} />
    </div>
  );
}

// ── Step 6: Initiatives ─────────────────────────────────────────────────────
function Step6({
  initiatives,
  onInitiativesChange,
  onNext,
  onBack,
}: {
  initiatives: string;
  onInitiativesChange: (v: string) => void;
  onNext: () => void;
  onBack: () => void;
}) {
  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h3 className="text-base font-semibold mb-1">Current Initiatives & Priority Updates — Slide 6</h3>
        <p className="text-sm text-muted-foreground">
          List your current strategic initiatives (one per line). These will appear as numbered items on the slide.
        </p>
      </div>
      <textarea
        rows={10}
        value={initiatives}
        onChange={(e) => onInitiativesChange(e.target.value)}
        placeholder={`Meta: Visit Campaigns — Assess performance of Broad Visit + Indy North + Open House Campaigns\nMeta & Microsoft Data Integrity — Hubspot Sync QA\nHubspot Paid Media Dashboard\nGoogle: AI Max Test on Non Branded Search\nMeta: Save 50K Promo — Ending 2/28\nGoogle: LSA Ad Account Creations + Lead Scoring`}
        className="w-full rounded-lg border border-gray-200 px-4 py-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-[#1a2744]/30 font-mono"
      />
      <p className="text-xs text-gray-400">Each line becomes one numbered initiative on the slide.</p>
      <NavButtons onBack={onBack} onNext={onNext} nextLabel="Generate Report" nextIcon={<Sparkles className="h-4 w-4" />} />
    </div>
  );
}

// ── Step 7: Generate & Preview ──────────────────────────────────────────────
function Step7({
  year,
  month,
  locations,
  keyInsights,
  focusAreas,
  attribution,
  initiatives,
  onBack,
}: {
  year: number;
  month: number;
  locations: LocationRow[];
  keyInsights: string;
  focusAreas: string;
  attribution: AttributionAnswers;
  initiatives: string;
  onBack: () => void;
}) {
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<MonthlySlidesResponse | null>(null);
  const [error, setError] = useState("");
  const [activeSlide, setActiveSlide] = useState(1);

  // Export state
  const [slidesLoading, setSlidesLoading] = useState(false);
  const [slidesError, setSlidesError] = useState("");
  const [pptxLoading, setPptxLoading] = useState(false);
  const [htmlLoading, setHtmlLoading] = useState(false);

  const { start, end } = monthStartEnd(year, month);

  const generate = useCallback(async () => {
    setLoading(true);
    setError("");
    setReport(null);

    const payload = {
      start_date: start,
      end_date: end,
      report_month_label: `${MONTHS[month - 1]} ${year}`,
      slide3_locations: locations.filter((l) => l.location.trim()),
      slide3_key_insights: keyInsights,
      slide3_focus_areas: focusAreas,
      slide4_attribution: attribution,
      slide6_initiatives: initiatives,
    };

    try {
      const res = await fetch(`${API_BASE}/api/reports/monthly-slides`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text);
      }
      const data: MonthlySlidesResponse = await res.json();
      setReport(data);
      setActiveSlide(1);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [start, end, month, year, locations, keyInsights, focusAreas, attribution, initiatives]);

  // ── Export handlers ──────────────────────────────────────────────────────
  const handleOpenGoogleSlides = useCallback(async () => {
    if (!report) return;
    setSlidesLoading(true);
    setSlidesError("");
    try {
      const res = await fetch(`${API_BASE}/api/reports/create-google-slides`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(report),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || res.statusText);
      }
      const data = await res.json();
      window.open(data.url, "_blank", "noopener,noreferrer");
    } catch (e) {
      setSlidesError(String(e instanceof Error ? e.message : e));
    } finally {
      setSlidesLoading(false);
    }
  }, [report]);

  const handleDownloadPptx = useCallback(async () => {
    if (!report) return;
    setPptxLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/reports/download-pptx`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(report),
      });
      if (!res.ok) throw new Error(res.statusText);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Schumacher Homes - ${MONTHS[month - 1]} ${year} Report.pptx`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      // silent — browser will show default error
    } finally {
      setPptxLoading(false);
    }
  }, [report, month, year]);

  const handleDownloadHtml = useCallback(async () => {
    if (!report) return;
    setHtmlLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/reports/download-html`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(report),
      });
      if (!res.ok) throw new Error(res.statusText);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Schumacher Homes - ${MONTHS[month - 1]} ${year} Report.html`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      // silent — browser will show default error
    } finally {
      setHtmlLoading(false);
    }
  }, [report, month, year]);

  return (
    <div className="space-y-6 max-w-5xl">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold mb-1">Monthly Report — {MONTHS[month - 1]} {year}</h3>
          <p className="text-sm text-muted-foreground">
            JARVIS will fetch live platform data, apply AI analysis, and render all 7 slides.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={onBack}
            disabled={loading}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg border border-gray-200 text-sm font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-40"
          >
            <ChevronLeft className="h-4 w-4" /> Back
          </button>
          <button
            onClick={generate}
            disabled={loading}
            className={`flex items-center gap-2 px-5 py-2 rounded-lg font-medium text-sm transition-all ${
              loading
                ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                : "bg-[#1a2744] text-white hover:bg-[#1a2744]/90 shadow"
            }`}
          >
            {loading ? (
              <><RefreshCw className="h-4 w-4 animate-spin" /> Generating slides...</>
            ) : (
              <><Sparkles className="h-4 w-4" /> {report ? "Regenerate" : "Generate Report"}</>
            )}
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 whitespace-pre-wrap">{error}</div>
      )}

      {loading && (
        <div className="flex flex-col items-center py-16 gap-4 text-center">
          <RefreshCw className="h-10 w-10 text-[#1a2744] animate-spin" />
          <p className="text-sm font-medium text-gray-600">Fetching live platform data and generating slides with JARVIS...</p>
          <p className="text-xs text-gray-400">This may take 15-30 seconds</p>
        </div>
      )}

      {report && !loading && (
        <div className="space-y-4">
          {/* Slide tab bar */}
          <div className="flex gap-1.5 flex-wrap">
            {report.slides.map((slide) => (
              <button
                key={slide.slide_number}
                onClick={() => setActiveSlide(slide.slide_number)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  activeSlide === slide.slide_number
                    ? "bg-[#1a2744] text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                Slide {slide.slide_number}: {slide.title.split(" ").slice(0, 3).join(" ")}
              </button>
            ))}
          </div>

          {/* Active slide */}
          {report.slides
            .filter((s) => s.slide_number === activeSlide)
            .map((slide) => (
              <SlidePreview key={slide.slide_number} slide={slide} apiBase={API_BASE} />
            ))}

          {/* Navigation between slides */}
          <div className="flex justify-between items-center pt-2">
            <button
              onClick={() => setActiveSlide((p) => Math.max(1, p - 1))}
              disabled={activeSlide === 1}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-30"
            >
              <ChevronLeft className="h-4 w-4" /> Previous Slide
            </button>
            <span className="text-xs text-gray-400">Slide {activeSlide} of {report.slides.length}</span>
            <button
              onClick={() => setActiveSlide((p) => Math.min(report.slides.length, p + 1))}
              disabled={activeSlide === report.slides.length}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-30"
            >
              Next Slide <ChevronRight className="h-4 w-4" />
            </button>
          </div>

          {/* ── Export bar ── */}
          <div className="flex flex-col gap-3 pt-3 border-t border-gray-100">
            <div className="flex items-center gap-3 flex-wrap">
              {/* HTML Report — primary export */}
              <button
                onClick={handleDownloadHtml}
                disabled={htmlLoading}
                className={`flex items-center gap-2 px-5 py-2.5 rounded-lg font-semibold text-sm transition-all shadow-md ${
                  htmlLoading
                    ? "bg-[#1a2744]/60 text-white/60 cursor-not-allowed"
                    : "bg-[#1a2744] text-white hover:bg-[#243564] active:scale-[0.98]"
                }`}
              >
                {htmlLoading ? (
                  <><RefreshCw className="h-4 w-4 animate-spin" /> Generating HTML...</>
                ) : (
                  <><Globe className="h-4 w-4" /> Download HTML Report <span className="ml-1 text-[#D4601A] font-bold">✦</span></>
                )}
              </button>

              {/* Google Slides */}
              <button
                onClick={handleOpenGoogleSlides}
                disabled={slidesLoading}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-lg font-medium text-sm transition-all shadow-sm ${
                  slidesLoading
                    ? "bg-gray-100 text-gray-400 cursor-not-allowed border border-gray-200"
                    : "bg-white border border-gray-200 text-gray-700 hover:bg-gray-50 hover:border-gray-300"
                }`}
              >
                {slidesLoading ? (
                  <><RefreshCw className="h-4 w-4 animate-spin text-[#1a2744]" /> Creating Slides...</>
                ) : (
                  <>
                    {/* Google Slides icon */}
                    <svg className="h-4 w-4" viewBox="0 0 48 48" fill="none">
                      <rect width="48" height="48" rx="4" fill="#F9AB00"/>
                      <path d="M12 8h24v32H12z" fill="white"/>
                      <rect x="16" y="16" width="16" height="2.5" rx="1.25" fill="#F9AB00"/>
                      <rect x="16" y="21" width="16" height="2.5" rx="1.25" fill="#F9AB00"/>
                      <rect x="16" y="26" width="10" height="2.5" rx="1.25" fill="#F9AB00"/>
                    </svg>
                    Open in Google Slides
                  </>
                )}
              </button>

              {/* Download PPTX */}
              <button
                onClick={handleDownloadPptx}
                disabled={pptxLoading}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-lg font-medium text-sm transition-all border ${
                  pptxLoading
                    ? "bg-gray-100 text-gray-400 cursor-not-allowed border-gray-200"
                    : "border-gray-200 text-gray-600 hover:bg-gray-50 hover:border-gray-300"
                }`}
              >
                {pptxLoading ? (
                  <><RefreshCw className="h-4 w-4 animate-spin" /> Building .pptx...</>
                ) : (
                  <><Download className="h-4 w-4" /> Download .pptx</>
                )}
              </button>

              <span className="text-xs text-gray-400 hidden sm:block">
                HTML → open in browser → Print → Save as PDF
              </span>
            </div>

            {slidesError && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                <strong>Google Slides:</strong> {slidesError}
                {slidesError.includes("GOOGLE_SERVICE_ACCOUNT_JSON") && (
                  <span className="block mt-1 text-amber-600">
                    Set <code className="font-mono">GOOGLE_SERVICE_ACCOUNT_JSON</code> in the backend <code className="font-mono">.env</code> file with your Google Service Account key to enable this feature.
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Nav buttons ─────────────────────────────────────────────────────────────
function NavButtons({
  onBack,
  onNext,
  nextLabel = "Continue",
  nextIcon,
}: {
  onBack: () => void;
  onNext: () => void;
  nextLabel?: string;
  nextIcon?: React.ReactNode;
}) {
  return (
    <div className="flex gap-3 pt-2">
      <button
        onClick={onBack}
        className="flex items-center gap-1.5 px-4 py-2 rounded-lg border border-gray-200 text-sm font-medium text-gray-600 hover:bg-gray-50"
      >
        <ChevronLeft className="h-4 w-4" /> Back
      </button>
      <button
        onClick={onNext}
        className="flex items-center gap-2 px-5 py-2 rounded-lg bg-[#1a2744] text-white font-medium text-sm hover:bg-[#1a2744]/90"
      >
        {nextLabel} {nextIcon || <ChevronRight className="h-4 w-4" />}
      </button>
    </div>
  );
}

// ── Main wizard export ──────────────────────────────────────────────────────
export function MonthlyReportWizard() {
  const now = new Date();
  const defaultMonth = now.getMonth() === 0 ? 12 : now.getMonth(); // default to last month
  const defaultYear = now.getMonth() === 0 ? now.getFullYear() - 1 : now.getFullYear();

  const [step, setStep] = useState(1);
  const [year, setYear] = useState(defaultYear);
  const [month, setMonth] = useState(defaultMonth);
  const [locations, setLocations] = useState<LocationRow[]>(
    Array.from({ length: 8 }, () => emptyLocation())
  );
  const [keyInsights, setKeyInsights] = useState("");
  const [focusAreas, setFocusAreas] = useState("");
  const [attribution, setAttribution] = useState<AttributionAnswers>({
    google_sync_status: "On Track",
    meta_sync_status: "In Progress",
    microsoft_sync_status: "In Progress",
    pmax_status: "",
    meta_pixel_status: "Healthy",
    lead_scoring_status: "In Progress",
    hubspot_leads: 0,
    platform_leads: 0,
    hubspot_quotes: 0,
    platform_quotes: 0,
    action_items: "",
  });
  const [initiatives, setInitiatives] = useState("");

  const next = () => setStep((s) => Math.min(7, s + 1));
  const back = () => setStep((s) => Math.max(1, s - 1));

  return (
    <div>
      <StepBar current={step} />

      {step === 1 && (
        <Step1
          year={year} month={month}
          onYearChange={setYear} onMonthChange={setMonth}
          onNext={next}
        />
      )}
      {step === 2 && <Step2 year={year} month={month} onNext={next} onBack={back} />}
      {step === 3 && (
        <Step3
          locations={locations} onLocationsChange={setLocations}
          keyInsights={keyInsights} onKeyInsightsChange={setKeyInsights}
          focusAreas={focusAreas} onFocusAreasChange={setFocusAreas}
          onNext={next} onBack={back}
        />
      )}
      {step === 4 && (
        <Step4 answers={attribution} onAnswersChange={setAttribution} onNext={next} onBack={back} />
      )}
      {step === 5 && <Step5 year={year} month={month} onNext={next} onBack={back} />}
      {step === 6 && (
        <Step6
          initiatives={initiatives} onInitiativesChange={setInitiatives}
          onNext={next} onBack={back}
        />
      )}
      {step === 7 && (
        <Step7
          year={year} month={month}
          locations={locations}
          keyInsights={keyInsights} focusAreas={focusAreas}
          attribution={attribution}
          initiatives={initiatives}
          onBack={back}
        />
      )}
    </div>
  );
}
