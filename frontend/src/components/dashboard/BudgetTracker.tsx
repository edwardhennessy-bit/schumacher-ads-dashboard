"use client";

import { useState, useEffect, useCallback } from "react";
import {
  DollarSign,
  Settings2,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Minus,
  ChevronDown,
  ChevronRight,
  X,
} from "lucide-react";
import { api } from "@/lib/api";
import { formatCurrency } from "@/lib/mock-data";

// ── Types ─────────────────────────────────────────────────────────────────────

type PacingStatus = "ahead" | "behind" | "on_track" | "no_budget";

interface FunnelBucket {
  spend: number;
  campaign_count: number;
}

interface PlatformStatus {
  budget: number;
  testing_budget: number;
  main_budget: number;
  total_spend: number;
  testing_spend: number;
  main_spend: number;
  remaining: number;
  expected_spend: number;
  pacing_factor: number;
  pacing_status: PacingStatus;
  testing_pacing_status: PacingStatus;
  funnel: {
    tof: FunnelBucket;
    mof: FunnelBucket;
    bof: FunnelBucket;
    testing: FunnelBucket;
    untagged: FunnelBucket;
  };
  campaign_count: number;
}

interface TestingCampaign {
  platform: string;
  name: string;
  spend: number;
}

interface BudgetStatus {
  start_date: string;
  end_date: string;
  pacing_factor: number;
  days_elapsed: number;
  days_in_month: number;
  platforms: {
    google: PlatformStatus;
    microsoft: PlatformStatus;
    meta: PlatformStatus;
  };
  overall_testing: {
    budget: number;
    total_spend: number;
    remaining: number;
    expected_spend: number;
    pacing_status: PacingStatus;
    campaigns: TestingCampaign[];
  };
}

interface PlatformBudgetInput {
  total: string;
  testing: string;
}

interface BudgetForm {
  google: PlatformBudgetInput;
  microsoft: PlatformBudgetInput;
  meta: PlatformBudgetInput;
  overall_testing: string;
}

// ── Sub-components ────────────────────────────────────────────────────────────

function PacingBadge({ status }: { status: PacingStatus }) {
  const styles: Record<PacingStatus, { label: string; classes: string; Icon: typeof TrendingUp }> = {
    on_track: { label: "On Track", classes: "bg-green-500/15 text-green-400", Icon: Minus },
    ahead:    { label: "Ahead of Pace", classes: "bg-amber-500/15 text-amber-400", Icon: TrendingUp },
    behind:   { label: "Behind Pace", classes: "bg-red-500/15 text-red-400", Icon: TrendingDown },
    no_budget: { label: "No Budget Set", classes: "bg-white/10 text-gray-500", Icon: Minus },
  };
  const { label, classes, Icon } = styles[status] ?? styles.no_budget;
  return (
    <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded font-medium ${classes}`}>
      <Icon className="h-3 w-3" />
      {label}
    </span>
  );
}

function ProgressBar({
  spend,
  budget,
  expected,
  color,
}: {
  spend: number;
  budget: number;
  expected: number;
  color: string;
}) {
  const spendPct = budget > 0 ? Math.min((spend / budget) * 100, 100) : 0;
  const expectedPct = budget > 0 ? Math.min((expected / budget) * 100, 100) : 0;
  return (
    <div className="relative h-2.5 bg-white/10 rounded-full overflow-hidden">
      {/* Expected pace marker */}
      {budget > 0 && (
        <div
          className="absolute top-0 h-full w-0.5 bg-white/30 z-10"
          style={{ left: `${expectedPct}%` }}
        />
      )}
      {/* Actual spend fill */}
      <div
        className={`h-full rounded-full transition-all duration-700 ${color}`}
        style={{ width: `${spendPct}%` }}
      />
    </div>
  );
}

function PlatformCard({
  label,
  color,
  accentBg,
  platform,
  pacing_factor,
}: {
  label: string;
  color: string;
  accentBg: string;
  platform: PlatformStatus;
  pacing_factor: number;
}) {
  const spendPct = platform.budget > 0 ? Math.min((platform.total_spend / platform.budget) * 100, 100) : 0;

  return (
    <div className={`rounded-xl border border-white/10 bg-[#252525] p-5 space-y-4`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className={`w-2.5 h-2.5 rounded-full ${accentBg}`} />
          <span className="font-semibold text-white">{label}</span>
        </div>
        <PacingBadge status={platform.pacing_status} />
      </div>

      {/* Spend vs Budget headline */}
      <div>
        <div className="flex items-end justify-between mb-1.5">
          <div>
            <span className="text-2xl font-bold text-white">{formatCurrency(platform.total_spend)}</span>
            {platform.budget > 0 && (
              <span className="text-sm text-gray-400 ml-1.5">/ {formatCurrency(platform.budget)}</span>
            )}
          </div>
          {platform.budget > 0 && (
            <span className="text-sm font-medium text-gray-300">{spendPct.toFixed(1)}%</span>
          )}
        </div>
        <ProgressBar
          spend={platform.total_spend}
          budget={platform.budget}
          expected={platform.expected_spend}
          color={color}
        />
        <div className="flex justify-between mt-1.5 text-xs text-gray-500">
          <span>Expected today: {formatCurrency(platform.expected_spend)}</span>
          {platform.budget > 0 && (
            <span className={platform.remaining >= 0 ? "text-gray-400" : "text-red-400"}>
              {platform.remaining >= 0
                ? `${formatCurrency(platform.remaining)} remaining`
                : `${formatCurrency(Math.abs(platform.remaining))} over budget`}
            </span>
          )}
        </div>
      </div>

      {/* Testing budget row */}
      {platform.testing_budget > 0 && (
        <div className="border-t border-white/5 pt-3 space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-400 font-medium uppercase tracking-wide">Testing Budget</span>
            <PacingBadge status={platform.testing_pacing_status} />
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-white font-medium">{formatCurrency(platform.testing_spend)}</span>
            <span className="text-gray-400">/ {formatCurrency(platform.testing_budget)}</span>
          </div>
          <ProgressBar
            spend={platform.testing_spend}
            budget={platform.testing_budget}
            expected={platform.testing_budget * pacing_factor}
            color="bg-purple-500"
          />
        </div>
      )}
    </div>
  );
}

function FunnelTable({
  google,
  microsoft,
  meta,
}: {
  google: PlatformStatus;
  microsoft: PlatformStatus;
  meta: PlatformStatus;
}) {
  const stages: Array<{ key: keyof PlatformStatus["funnel"]; label: string; description: string }> = [
    { key: "tof", label: "TOF", description: "Top of Funnel" },
    { key: "mof", label: "MOF", description: "Middle of Funnel" },
    { key: "bof", label: "BOF", description: "Bottom of Funnel" },
    { key: "testing", label: "Testing", description: "Test campaigns" },
    { key: "untagged", label: "Untagged", description: "No funnel tag" },
  ];

  const googleTotal = google.total_spend || 1;
  const msTotal = microsoft.total_spend || 1;
  const metaTotal = meta.total_spend || 1;

  return (
    <div className="rounded-xl border border-white/10 bg-[#252525] overflow-hidden">
      <div className="px-5 py-4 border-b border-white/5">
        <h3 className="font-semibold text-white">Funnel Breakdown</h3>
        <p className="text-xs text-gray-500 mt-0.5">Spend distribution by campaign funnel stage across all platforms</p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/5">
              <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide w-40">Stage</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-green-500 uppercase tracking-wide">Google</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-[#f27038] uppercase tracking-wide">Microsoft</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-blue-400 uppercase tracking-wide">Meta</th>
              <th className="px-5 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wide">Total</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {stages.map(({ key, label, description }) => {
              const g = google.funnel?.[key] ?? { spend: 0, campaign_count: 0 };
              const ms = microsoft.funnel?.[key] ?? { spend: 0, campaign_count: 0 };
              const m = meta.funnel?.[key] ?? { spend: 0, campaign_count: 0 };
              const rowTotal = g.spend + ms.spend + m.spend;
              const hasData = rowTotal > 0;

              return (
                <tr key={key} className={`hover:bg-white/5 transition-colors ${!hasData ? "opacity-40" : ""}`}>
                  <td className="px-5 py-3.5">
                    <div>
                      <span className={`inline-block text-xs font-bold px-1.5 py-0.5 rounded mr-2 ${
                        key === "tof" ? "bg-blue-500/20 text-blue-300" :
                        key === "mof" ? "bg-purple-500/20 text-purple-300" :
                        key === "bof" ? "bg-green-500/20 text-green-300" :
                        key === "testing" ? "bg-amber-500/20 text-amber-300" :
                        "bg-white/10 text-gray-400"
                      }`}>{label}</span>
                      <span className="text-gray-500 text-xs">{description}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3.5 text-right">
                    <div className="text-white font-medium">{hasData && g.spend > 0 ? formatCurrency(g.spend) : "—"}</div>
                    {g.spend > 0 && (
                      <div className="text-xs text-gray-500">{((g.spend / googleTotal) * 100).toFixed(1)}% · {g.campaign_count}c</div>
                    )}
                  </td>
                  <td className="px-4 py-3.5 text-right">
                    <div className="text-white font-medium">{hasData && ms.spend > 0 ? formatCurrency(ms.spend) : "—"}</div>
                    {ms.spend > 0 && (
                      <div className="text-xs text-gray-500">{((ms.spend / msTotal) * 100).toFixed(1)}% · {ms.campaign_count}c</div>
                    )}
                  </td>
                  <td className="px-4 py-3.5 text-right">
                    <div className="text-white font-medium">{hasData && m.spend > 0 ? formatCurrency(m.spend) : "—"}</div>
                    {m.spend > 0 && (
                      <div className="text-xs text-gray-500">{((m.spend / metaTotal) * 100).toFixed(1)}% · {m.campaign_count}c</div>
                    )}
                  </td>
                  <td className="px-5 py-3.5 text-right">
                    <div className={`font-semibold ${hasData ? "text-white" : "text-gray-600"}`}>
                      {hasData ? formatCurrency(rowTotal) : "—"}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
          {/* Totals footer */}
          <tfoot>
            <tr className="border-t border-white/10 bg-white/5">
              <td className="px-5 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide">Total</td>
              <td className="px-4 py-3 text-right font-bold text-green-400">{formatCurrency(google.total_spend)}</td>
              <td className="px-4 py-3 text-right font-bold text-[#f27038]">{formatCurrency(microsoft.total_spend)}</td>
              <td className="px-4 py-3 text-right font-bold text-blue-400">{formatCurrency(meta.total_spend)}</td>
              <td className="px-5 py-3 text-right font-bold text-white">
                {formatCurrency(google.total_spend + microsoft.total_spend + meta.total_spend)}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}

function BudgetConfigModal({
  onClose,
  onSaved,
}: {
  onClose: () => void;
  onSaved: () => void;
}) {
  const [form, setForm] = useState<BudgetForm>({
    google:    { total: "", testing: "" },
    microsoft: { total: "", testing: "" },
    meta:      { total: "", testing: "" },
    overall_testing: "",
  });
  const [saving, setSaving] = useState(false);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    api.getBudgetConfig().then((cfg) => {
      setForm({
        google:    { total: cfg.google.total > 0 ? String(cfg.google.total) : "", testing: cfg.google.testing > 0 ? String(cfg.google.testing) : "" },
        microsoft: { total: cfg.microsoft.total > 0 ? String(cfg.microsoft.total) : "", testing: cfg.microsoft.testing > 0 ? String(cfg.microsoft.testing) : "" },
        meta:      { total: cfg.meta.total > 0 ? String(cfg.meta.total) : "", testing: cfg.meta.testing > 0 ? String(cfg.meta.testing) : "" },
        overall_testing: cfg.overall_testing_budget > 0 ? String(cfg.overall_testing_budget) : "",
      });
      setLoaded(true);
    }).catch(() => setLoaded(true));
  }, []);

  const set = (platform: keyof BudgetForm, field: keyof PlatformBudgetInput, val: string) => {
    setForm((f) => ({ ...f, [platform]: { ...f[platform], [field]: val } }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.saveBudgetConfig({
        google:    { total: parseFloat(form.google.total) || 0,    testing: parseFloat(form.google.testing) || 0 },
        microsoft: { total: parseFloat(form.microsoft.total) || 0, testing: parseFloat(form.microsoft.testing) || 0 },
        meta:      { total: parseFloat(form.meta.total) || 0,      testing: parseFloat(form.meta.testing) || 0 },
        overall_testing_budget: parseFloat(form.overall_testing) || 0,
      });
      onSaved();
      onClose();
    } finally {
      setSaving(false);
    }
  };

  const platforms: Array<{ key: keyof BudgetForm; label: string; accent: string }> = [
    { key: "google",    label: "Google Ads",    accent: "border-l-green-500" },
    { key: "microsoft", label: "Microsoft Ads", accent: "border-l-[#f27038]" },
    { key: "meta",      label: "Meta",          accent: "border-l-blue-400" },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />

      {/* Modal */}
      <div className="relative w-full max-w-lg bg-[#1e1e1e] border border-white/10 rounded-2xl shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-white/10">
          <div>
            <h2 className="text-lg font-bold text-white">Set Monthly Budgets</h2>
            <p className="text-xs text-gray-400 mt-0.5">Enter the total and testing budget for each platform</p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-white/10 text-gray-400 hover:text-white transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Form */}
        <div className="px-6 py-5 space-y-5">
          {!loaded ? (
            <div className="text-center py-8 text-gray-500 text-sm">Loading current config...</div>
          ) : (
            platforms.map(({ key, label, accent }) => (
              <div key={key} className={`border-l-4 ${accent} pl-4 space-y-3`}>
                <h3 className="font-semibold text-white text-sm">{label}</h3>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Total Monthly Budget</label>
                    <div className="relative">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm">$</span>
                      <input
                        type="number"
                        placeholder="0"
                        value={form[key].total}
                        onChange={(e) => set(key, "total", e.target.value)}
                        className="w-full pl-7 pr-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:border-[#f27038] placeholder:text-gray-600"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Platform Testing <span className="text-gray-600">(subset)</span></label>
                    <div className="relative">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm">$</span>
                      <input
                        type="number"
                        placeholder="0"
                        value={form[key].testing}
                        onChange={(e) => set(key, "testing", e.target.value)}
                        className="w-full pl-7 pr-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:border-[#f27038] placeholder:text-gray-600"
                      />
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}

          {/* Overall creative testing budget — cross-platform */}
          {loaded && (
            <div className="border-t border-white/10 pt-5">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-2 h-2 rounded-full bg-amber-400" />
                <h3 className="font-semibold text-white text-sm">Overall Creative Testing Budget</h3>
                <span className="text-xs text-gray-500">— applies across all platforms</span>
              </div>
              <p className="text-xs text-gray-500 mb-3">
                Campaigns tagged with "TEST" on any platform roll up here. Set the total budget you have allocated for creative testing across Google, Microsoft, and Meta combined.
              </p>
              <div className="relative max-w-xs">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm">$</span>
                <input
                  type="number"
                  placeholder="0"
                  value={form.overall_testing}
                  onChange={(e) => setForm((f) => ({ ...f, overall_testing: e.target.value }))}
                  className="w-full pl-7 pr-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:border-amber-400 placeholder:text-gray-600"
                />
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-white/10 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !loaded}
            className="px-5 py-2 bg-[#f27038] hover:bg-[#e05f27] text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save Budgets"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Creative Testing Section ──────────────────────────────────────────────────

const PLATFORM_LABELS: Record<string, { label: string; color: string }> = {
  google:    { label: "Google",    color: "text-green-400" },
  microsoft: { label: "Microsoft", color: "text-[#f27038]" },
  meta:      { label: "Meta",      color: "text-blue-400" },
};

function CreativeTestingSection({
  testing,
}: {
  testing: BudgetStatus["overall_testing"];
}) {
  const spendPct = testing.budget > 0 ? Math.min((testing.total_spend / testing.budget) * 100, 100) : 0;
  const hasCampaigns = testing.campaigns.length > 0;

  return (
    <div className="rounded-xl border border-amber-500/20 bg-[#252525] overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-white/5">
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-amber-400" />
          <h3 className="font-semibold text-white">Creative Testing</h3>
          <span className="text-xs text-gray-500">cross-platform</span>
        </div>
        <PacingBadge status={testing.pacing_status} />
      </div>

      <div className="px-5 py-4 space-y-4">
        {/* Budget vs spend */}
        <div>
          <div className="flex items-end justify-between mb-1.5">
            <div>
              <span className="text-2xl font-bold text-white">{formatCurrency(testing.total_spend)}</span>
              {testing.budget > 0 && (
                <span className="text-sm text-gray-400 ml-1.5">/ {formatCurrency(testing.budget)}</span>
              )}
            </div>
            {testing.budget > 0 && (
              <span className="text-sm font-medium text-gray-300">{spendPct.toFixed(1)}%</span>
            )}
          </div>
          <ProgressBar
            spend={testing.total_spend}
            budget={testing.budget}
            expected={testing.expected_spend}
            color="bg-amber-400"
          />
          <div className="flex justify-between mt-1.5 text-xs text-gray-500">
            <span>Expected today: {formatCurrency(testing.expected_spend)}</span>
            {testing.budget > 0 && (
              <span className={testing.remaining >= 0 ? "text-gray-400" : "text-red-400"}>
                {testing.remaining >= 0
                  ? `${formatCurrency(testing.remaining)} remaining`
                  : `${formatCurrency(Math.abs(testing.remaining))} over budget`}
              </span>
            )}
          </div>
        </div>

        {/* Campaign breakdown */}
        {hasCampaigns ? (
          <div>
            <p className="text-xs text-gray-500 mb-2 uppercase tracking-wide font-medium">Campaigns identified</p>
            <div className="space-y-1.5">
              {testing.campaigns.map((c, i) => {
                const pl = PLATFORM_LABELS[c.platform] ?? { label: c.platform, color: "text-gray-400" };
                return (
                  <div key={i} className="flex items-center justify-between py-1.5 px-3 rounded-lg bg-white/5">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className={`text-xs font-semibold shrink-0 ${pl.color}`}>{pl.label}</span>
                      <span className="text-sm text-gray-300 truncate">{c.name}</span>
                    </div>
                    <span className="text-sm font-medium text-white shrink-0 ml-3">{formatCurrency(c.spend)}</span>
                  </div>
                );
              })}
            </div>
          </div>
        ) : (
          <p className="text-xs text-gray-500 italic">
            No campaigns tagged with "TEST" found across platforms for this period.
          </p>
        )}
      </div>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────

interface BudgetTrackerProps {
  startDate?: string;
  endDate?: string;
}

export function BudgetTracker({ startDate, endDate }: BudgetTrackerProps) {
  const [status, setStatus] = useState<BudgetStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [showConfig, setShowConfig] = useState(false);
  const [funnelExpanded, setFunnelExpanded] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getBudgetStatus(startDate, endDate);
      setStatus(data as BudgetStatus);
    } catch (e) {
      console.error("Budget status fetch error:", e);
    } finally {
      setLoading(false);
    }
  }, [startDate, endDate]);

  useEffect(() => { load(); }, [load]);

  const platforms: Array<{ key: keyof BudgetStatus["platforms"]; label: string; color: string; accentBg: string }> = [
    { key: "google",    label: "Google Ads",    color: "bg-green-500",    accentBg: "bg-green-500" },
    { key: "microsoft", label: "Microsoft Ads", color: "bg-[#f27038]",   accentBg: "bg-[#f27038]" },
    { key: "meta",      label: "Meta",          color: "bg-blue-400",    accentBg: "bg-blue-400" },
  ];

  const totalBudget = status
    ? (status.platforms.google.budget + status.platforms.microsoft.budget + status.platforms.meta.budget)
    : 0;
  const totalSpend = status
    ? (status.platforms.google.total_spend + status.platforms.microsoft.total_spend + status.platforms.meta.total_spend)
    : 0;

  return (
    <>
      {showConfig && (
        <BudgetConfigModal
          onClose={() => setShowConfig(false)}
          onSaved={load}
        />
      )}

      <div className="space-y-4">
        {/* Section header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-white">Budget Tracker</h2>
            {status && (
              <p className="text-xs text-gray-500 mt-0.5">
                Day {status.days_elapsed} of {status.days_in_month} &middot;{" "}
                {(status.pacing_factor * 100).toFixed(1)}% through the month
                {totalBudget > 0 && (
                  <> &middot; <span className="text-gray-400">{formatCurrency(totalSpend)} of {formatCurrency(totalBudget)} total</span></>
                )}
              </p>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={load}
              disabled={loading}
              className="p-2 rounded-lg hover:bg-white/10 text-gray-400 hover:text-white transition-colors disabled:opacity-40"
              title="Refresh"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            </button>
            <button
              onClick={() => setShowConfig(true)}
              className="flex items-center gap-2 px-3 py-2 bg-white/5 hover:bg-white/10 border border-white/10 text-gray-300 hover:text-white text-sm rounded-lg transition-colors"
            >
              <Settings2 className="h-4 w-4" />
              Set Budgets
            </button>
          </div>
        </div>

        {loading && !status ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-44 rounded-xl bg-white/5 animate-pulse" />
            ))}
          </div>
        ) : status ? (
          <>
            {/* Platform cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {platforms.map(({ key, label, color, accentBg }) => (
                <PlatformCard
                  key={key}
                  label={label}
                  color={color}
                  accentBg={accentBg}
                  platform={status.platforms[key]}
                  pacing_factor={status.pacing_factor}
                />
              ))}
            </div>

            {/* Creative Testing — cross-platform */}
            <CreativeTestingSection testing={status.overall_testing} />

            {/* Funnel breakdown — collapsible */}
            <div>
              <button
                onClick={() => setFunnelExpanded((v) => !v)}
                className="flex items-center gap-2 text-sm text-gray-400 hover:text-white mb-3 transition-colors"
              >
                {funnelExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                Funnel Breakdown by Platform
              </button>
              {funnelExpanded && (
                <FunnelTable
                  google={status.platforms.google}
                  microsoft={status.platforms.microsoft}
                  meta={status.platforms.meta}
                />
              )}
            </div>

            {/* No budget notice */}
            {totalBudget === 0 && (
              <div className="text-center py-4 text-sm text-gray-500">
                No budgets set yet.{" "}
                <button onClick={() => setShowConfig(true)} className="text-[#f27038] hover:underline">
                  Set monthly budgets
                </button>{" "}
                to see pacing and remaining spend.
              </div>
            )}
          </>
        ) : (
          <div className="text-center py-8 text-sm text-gray-500">Could not load budget data.</div>
        )}
      </div>
    </>
  );
}
