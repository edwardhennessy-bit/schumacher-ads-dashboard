"use client";

import { formatCurrency, formatNumber } from "@/lib/mock-data";

interface SlideContent {
  slide_number: number;
  title: string;
  content: Record<string, unknown>;
}

interface Creative {
  ad_id: string;
  ad_name: string;
  campaign_name: string;
  spend: number;
  leads: number;
  clicks: number;
  impressions: number;
  cpl: number | null;
  ctr: number;
  thumbnail_url: string;
  image_url: string;
}

interface SlidePreviewProps {
  slide: SlideContent;
  apiBase?: string;
}

// ── Shared slide chrome ─────────────────────────────────────────────────────
function SlideShell({
  slideNum,
  title,
  subtitle,
  children,
}: {
  slideNum: number;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-gray-200 overflow-hidden shadow-md bg-white">
      {/* Header bar matching the deck's dark navy */}
      <div className="bg-[#1a2744] px-6 py-4">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs text-blue-300 font-medium uppercase tracking-widest mb-0.5">
              Slide {slideNum}
            </p>
            <h2 className="text-xl font-bold text-white">{title}</h2>
            {subtitle && (
              <p className="text-xs text-blue-200 mt-0.5">{subtitle}</p>
            )}
          </div>
          <div className="text-xs text-blue-300 font-medium mt-1">
            Schumacher Homes
          </div>
        </div>
      </div>
      <div className="p-6">{children}</div>
    </div>
  );
}

// ── Slide 1: Title ──────────────────────────────────────────────────────────
function Slide1({ content }: { content: Record<string, unknown> }) {
  const agenda = (content.agenda as string[]) || [];
  return (
    <SlideShell slideNum={1} title={content.headline as string}>
      <div className="py-6">
        <h3 className="text-base font-semibold text-gray-700 mb-4 uppercase tracking-wide">Agenda</h3>
        <ol className="space-y-3">
          {agenda.map((item, i) => (
            <li key={i} className="flex items-start gap-3">
              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-[#1a2744] text-white text-xs flex items-center justify-center font-bold">
                {i + 1}
              </span>
              <span className="text-gray-700 font-medium pt-0.5">{item}</span>
            </li>
          ))}
        </ol>
      </div>
    </SlideShell>
  );
}

// ── Slide 2: KPI MoM ────────────────────────────────────────────────────────
function Slide2({ content }: { content: Record<string, unknown> }) {
  type MomRow = { metric: string; prev: string; curr: string; change: string; direction: string; invert: boolean };
  const rows = (content.mom_table as MomRow[]) || [];
  const summary = (content.summary_stats as Record<string, number>) || {};
  const prevLabel = (content.prev_month_label as string) || "Prev";
  const currLabel = (content.curr_month_label as string) || "Current";
  const takeaways = content.key_takeaways as string || "";
  const nextSteps = content.next_steps as string || "";

  const isMetricRow = (metric: string) =>
    ["Google Spend", "Meta Spend", "Microsoft Spend"].includes(metric);

  return (
    <SlideShell slideNum={2} title="Paid Media KPIs & MoM Analysis" subtitle={content.subtitle as string}>
      {/* Summary stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {[
          { label: "Total Leads", value: formatNumber(summary.total_leads ?? 0) },
          { label: "Blended CPL", value: formatCurrency(summary.blended_cpl ?? 0) },
          { label: "Total Spend", value: formatCurrency(summary.total_spend ?? 0) },
        ].map((s) => (
          <div key={s.label} className="rounded-lg bg-[#1a2744]/5 border border-[#1a2744]/10 p-4 text-center">
            <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">{s.label}</p>
            <p className="text-2xl font-bold text-[#1a2744]">{s.value}</p>
          </div>
        ))}
      </div>

      {/* MoM table */}
      <div className="overflow-x-auto mb-6">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-[#1a2744] text-white">
              <th className="px-4 py-2.5 text-left font-semibold">Metric</th>
              <th className="px-4 py-2.5 text-right font-semibold">{prevLabel}</th>
              <th className="px-4 py-2.5 text-right font-semibold">{currLabel}</th>
              <th className="px-4 py-2.5 text-right font-semibold">MoM Change</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => {
              const isSection = isMetricRow(row.metric);
              const isPositive = row.direction === "▲";
              const isGood = row.invert ? !isPositive : isPositive;
              return (
                <tr
                  key={i}
                  className={`border-b border-gray-100 ${
                    isSection ? "bg-gray-50 font-semibold" : "hover:bg-gray-50"
                  }`}
                >
                  <td className="px-4 py-2.5 text-gray-800">
                    {isSection && (
                      <span className="inline-block w-2 h-2 rounded-full bg-[#1a2744] mr-2" />
                    )}
                    {row.metric}
                  </td>
                  <td className="px-4 py-2.5 text-right text-gray-600">{row.prev}</td>
                  <td className="px-4 py-2.5 text-right font-medium">{row.curr}</td>
                  <td className="px-4 py-2.5 text-right">
                    <span className={`font-semibold ${isGood ? "text-green-600" : "text-red-500"}`}>
                      {row.change} {row.direction}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Key Takeaways */}
      {takeaways && (
        <div className="grid grid-cols-2 gap-4">
          <div className="rounded-lg bg-blue-50 border border-blue-100 p-4">
            <h4 className="text-xs font-bold uppercase tracking-wide text-blue-700 mb-2">Key Takeaways</h4>
            <div className="text-sm text-gray-700 space-y-1 whitespace-pre-line">{takeaways}</div>
          </div>
          {nextSteps && (
            <div className="rounded-lg bg-green-50 border border-green-100 p-4">
              <h4 className="text-xs font-bold uppercase tracking-wide text-green-700 mb-2">Next Steps</h4>
              <div className="text-sm text-gray-700 whitespace-pre-line">{nextSteps}</div>
            </div>
          )}
        </div>
      )}
    </SlideShell>
  );
}

// ── Slide 3: Design Center Scorecard ───────────────────────────────────────
function Slide3({ content }: { content: Record<string, unknown> }) {
  type LocRow = { location: string; leads: number; visits: number; cpl: number; quotes: number; spend: number };
  const summary = (content.summary_stats as Record<string, number>) || {};
  const topPerformers = (content.top_performers as LocRow[]) || [];
  const needsAttention = (content.needs_attention as LocRow[]) || [];
  const insights = content.key_insights as string || "";
  const focusAreas = content.focus_areas as string || "";

  const LocTable = ({ rows, label, color }: { rows: LocRow[]; label: string; color: string }) => (
    <div className="mb-4">
      <h4 className={`text-xs font-bold uppercase tracking-wide mb-2 ${color}`}>{label}</h4>
      {rows.length === 0 ? (
        <p className="text-xs text-gray-400 italic">No data provided</p>
      ) : (
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-gray-100">
              {["Location", "Leads", "Visits", "CPL", "Quotes", "Spend"].map((h) => (
                <th key={h} className={`px-3 py-1.5 text-left font-semibold text-gray-600 ${h !== "Location" ? "text-right" : ""}`}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="px-3 py-1.5 font-medium">{row.location}</td>
                <td className="px-3 py-1.5 text-right">{row.leads}</td>
                <td className="px-3 py-1.5 text-right">{row.visits}</td>
                <td className="px-3 py-1.5 text-right">{formatCurrency(row.cpl)}</td>
                <td className="px-3 py-1.5 text-right">{row.quotes}</td>
                <td className="px-3 py-1.5 text-right">{formatCurrency(row.spend)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );

  return (
    <SlideShell slideNum={3} title="Design Center Scorecard" subtitle={content.subtitle as string}>
      {/* Summary stats */}
      <div className="grid grid-cols-5 gap-3 mb-6">
        {[
          { label: "Total Leads", value: formatNumber(summary.total_leads ?? 0) },
          { label: "Avg CPL", value: formatCurrency(summary.avg_cpl ?? 0) },
          { label: "Total Visits", value: formatNumber(summary.total_visits ?? 0) },
          { label: "Cost / Visit", value: formatCurrency(summary.cost_per_visit ?? 0) },
          { label: "Total Quotes", value: formatNumber(summary.total_quotes ?? 0) },
        ].map((s) => (
          <div key={s.label} className="rounded-lg bg-[#1a2744]/5 border border-[#1a2744]/10 p-3 text-center">
            <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">{s.label}</p>
            <p className="text-xl font-bold text-[#1a2744]">{s.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-6 mb-4">
        <LocTable rows={topPerformers} label="Top Performers — Leads & Visits" color="text-green-700" />
        <LocTable rows={needsAttention} label="Needs Attention — Low Volume or High CPL" color="text-amber-700" />
      </div>

      {insights && (
        <div className="grid grid-cols-2 gap-4">
          <div className="rounded-lg bg-blue-50 border border-blue-100 p-4">
            <h4 className="text-xs font-bold uppercase tracking-wide text-blue-700 mb-2">Key Insights</h4>
            <div className="text-sm text-gray-700 whitespace-pre-line">{insights}</div>
          </div>
          {focusAreas && (
            <div className="rounded-lg bg-amber-50 border border-amber-100 p-4">
              <h4 className="text-xs font-bold uppercase tracking-wide text-amber-700 mb-2">Focus Areas</h4>
              <div className="text-sm text-gray-700 whitespace-pre-line">{focusAreas}</div>
            </div>
          )}
        </div>
      )}
    </SlideShell>
  );
}

// ── Slide 4: Attribution & Data Integrity ──────────────────────────────────
function Slide4({ content }: { content: Record<string, unknown> }) {
  type AccuracyRow = { metric: string; platform: number; hubspot: number; variance: string; accuracy: string; on_target: boolean | null };
  const sync = (content.hubspot_sync as Record<string, string>) || {};
  const accuracyTable = (content.accuracy_table as AccuracyRow[]) || [];
  const actionItems = (content.action_items as string[]) || [];

  const statusBadge = (status: string) => {
    const lower = status.toLowerCase();
    if (lower.includes("on track") || lower.includes("healthy")) {
      return <span className="px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700">{status}</span>;
    }
    if (lower.includes("progress")) {
      return <span className="px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-700">{status}</span>;
    }
    return <span className="px-2 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-700">{status}</span>;
  };

  return (
    <SlideShell slideNum={4} title="Attribution & Data Integrity">
      <div className="grid grid-cols-2 gap-6">
        <div className="space-y-4">
          {/* HubSpot sync status */}
          <div className="rounded-lg border p-4">
            <h4 className="text-xs font-bold uppercase tracking-wide text-gray-500 mb-3">HubSpot Attribution Sync</h4>
            <div className="space-y-2">
              {[
                { label: "Google", status: sync.google_status },
                { label: "Meta", status: sync.meta_status },
                { label: "Microsoft", status: sync.microsoft_status },
              ].map((item) => (
                <div key={item.label} className="flex items-center justify-between">
                  <span className="text-sm font-medium">{item.label}:</span>
                  {statusBadge(item.status || "Unknown")}
                </div>
              ))}
            </div>
          </div>

          {/* Lead/Quote accuracy table */}
          <div className="rounded-lg border p-4">
            <h4 className="text-xs font-bold uppercase tracking-wide text-gray-500 mb-3">Platform vs HubSpot (Target: 85%+)</h4>
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-gray-50">
                  {["Metric", "Platform", "HubSpot", "Variance", "Accuracy"].map((h) => (
                    <th key={h} className="px-2 py-1.5 text-left font-semibold text-gray-600">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {accuracyTable.map((row, i) => (
                  <tr key={i} className="border-b border-gray-100">
                    <td className="px-2 py-1.5 font-medium">{row.metric}</td>
                    <td className="px-2 py-1.5">{row.platform.toLocaleString()}</td>
                    <td className="px-2 py-1.5">{row.hubspot.toLocaleString()}</td>
                    <td className="px-2 py-1.5 text-gray-500">{row.variance}</td>
                    <td className="px-2 py-1.5">
                      {row.on_target === null ? (
                        <span className="text-gray-400">—</span>
                      ) : row.on_target ? (
                        <span className="text-green-600 font-semibold">{row.accuracy} ✓</span>
                      ) : (
                        <span className="text-red-500 font-semibold">{row.accuracy} ✗</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="space-y-4">
          {/* Status items */}
          {[
            { label: "PMax Attribution", value: content.pmax_status as string, icon: "📊" },
            { label: "Meta Pixel Health", value: content.meta_pixel_status as string, icon: "📡" },
            { label: "Lead Scoring", value: content.lead_scoring_status as string, icon: "🎯" },
          ].map((item) => item.value && (
            <div key={item.label} className="rounded-lg border p-4">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-semibold">{item.icon} {item.label}</span>
                {statusBadge(item.value)}
              </div>
            </div>
          ))}

          {/* Action items */}
          {actionItems.length > 0 && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
              <h4 className="text-xs font-bold uppercase tracking-wide text-amber-700 mb-2">Action Items</h4>
              <ul className="space-y-1.5">
                {actionItems.map((item, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                    <span className="text-amber-500 mt-0.5">→</span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </SlideShell>
  );
}

// ── Slide 5: Ad Development & Testing ──────────────────────────────────────
function Slide5({ content, apiBase }: { content: Record<string, unknown>; apiBase?: string }) {
  const creatives = (content.creatives as Creative[]) || [];

  return (
    <SlideShell slideNum={5} title="Ad Development & Testing" subtitle={content.subtitle as string}>
      {creatives.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <p className="text-sm">No creative data available for this period.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {creatives.map((creative, i) => {
            const thumbSrc = creative.thumbnail_url || creative.image_url;
            const proxyUrl = thumbSrc && apiBase
              ? `${apiBase}/api/media/proxy?url=${encodeURIComponent(thumbSrc)}`
              : thumbSrc;

            return (
              <div key={creative.ad_id} className="rounded-lg border overflow-hidden bg-white shadow-sm">
                {/* Creative image */}
                <div className="relative h-40 bg-gray-100">
                  {proxyUrl ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={proxyUrl}
                      alt={creative.ad_name}
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = "none";
                      }}
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-gray-300">
                      <span className="text-4xl">🖼</span>
                    </div>
                  )}
                  <div className="absolute top-2 left-2 bg-[#1a2744] text-white text-xs px-2 py-0.5 rounded font-bold">
                    #{i + 1}
                  </div>
                </div>

                {/* Creative info */}
                <div className="p-3">
                  <p className="text-xs font-semibold text-gray-800 line-clamp-2 mb-1">{creative.ad_name}</p>
                  <p className="text-xs text-gray-400 line-clamp-1 mb-2">{creative.campaign_name}</p>
                  <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
                    {[
                      { label: "Leads", value: formatNumber(creative.leads) },
                      { label: "CPL", value: creative.cpl ? formatCurrency(creative.cpl) : "—" },
                      { label: "Spend", value: formatCurrency(creative.spend) },
                      { label: "CTR", value: `${creative.ctr}%` },
                      { label: "Clicks", value: formatNumber(creative.clicks) },
                      { label: "Impressions", value: formatNumber(creative.impressions) },
                    ].map((m) => (
                      <div key={m.label}>
                        <span className="text-gray-400">{m.label}: </span>
                        <span className="font-semibold text-gray-700">{m.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
      {content.note && (
        <p className="text-xs text-gray-400 mt-3 italic">{content.note as string}</p>
      )}
    </SlideShell>
  );
}

// ── Slide 6: Current Initiatives ───────────────────────────────────────────
function Slide6({ content }: { content: Record<string, unknown> }) {
  const initiatives = (content.initiatives as string[]) || [];
  return (
    <SlideShell slideNum={6} title="Current Initiatives & Priority Updates">
      {initiatives.length === 0 ? (
        <p className="text-sm text-gray-400 italic py-6 text-center">No initiatives provided.</p>
      ) : (
        <ol className="space-y-3 py-2">
          {initiatives.map((item, i) => (
            <li key={i} className="flex items-start gap-4">
              <span className="flex-shrink-0 w-8 h-8 rounded-full bg-[#1a2744] text-white font-bold text-sm flex items-center justify-center">
                {i + 1}
              </span>
              <div className="flex-1 rounded-lg bg-gray-50 border border-gray-100 px-4 py-2.5">
                <p className="text-sm text-gray-800 font-medium">{item}</p>
              </div>
            </li>
          ))}
        </ol>
      )}
    </SlideShell>
  );
}

// ── Slide 7: Strategic Recommendations ─────────────────────────────────────
function Slide7({ content }: { content: Record<string, unknown> }) {
  type Rec = { title: string; body: string };
  const recommendations = (content.recommendations as Rec[]) || [];
  const whatsNext = content.whats_next as string || "";

  return (
    <SlideShell slideNum={7} title="Strategic Recommendations">
      {recommendations.length === 0 ? (
        <p className="text-sm text-gray-400 italic py-6 text-center">Generating recommendations...</p>
      ) : (
        <div className="space-y-4">
          {recommendations.map((rec, i) => (
            <div key={i} className="rounded-lg border border-[#1a2744]/20 bg-[#1a2744]/3 p-4">
              <h4 className="font-bold text-[#1a2744] mb-1.5">
                <span className="text-blue-400 mr-2">0{i + 1}</span>
                {rec.title}
              </h4>
              <p className="text-sm text-gray-700 leading-relaxed">{rec.body}</p>
            </div>
          ))}

          {whatsNext && (
            <div className="rounded-lg bg-green-50 border border-green-100 p-4 mt-2">
              <h4 className="text-xs font-bold uppercase tracking-wide text-green-700 mb-2">What&apos;s Next</h4>
              <p className="text-sm text-gray-700 leading-relaxed">{whatsNext}</p>
            </div>
          )}
        </div>
      )}
    </SlideShell>
  );
}

// ── Main export ─────────────────────────────────────────────────────────────
export function SlidePreview({ slide, apiBase }: SlidePreviewProps) {
  switch (slide.slide_number) {
    case 1: return <Slide1 content={slide.content} />;
    case 2: return <Slide2 content={slide.content} />;
    case 3: return <Slide3 content={slide.content} />;
    case 4: return <Slide4 content={slide.content} />;
    case 5: return <Slide5 content={slide.content} apiBase={apiBase} />;
    case 6: return <Slide6 content={slide.content} />;
    case 7: return <Slide7 content={slide.content} />;
    default: return null;
  }
}
