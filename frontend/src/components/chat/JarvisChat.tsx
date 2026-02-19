"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Send, Bot, User, Loader2, Trash2, Sparkles,
  PauseCircle, TrendingUp, AlertCircle, Copy, Check, Mail,
} from "lucide-react";
import { cn } from "@/lib/utils";

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  dataSource?: string;
}

interface PauseItem {
  ad_id?: string;
  ad_name: string;
  campaign: string;
  adset: string;
  days_running: number | null;
  spend_30d: number;
  leads_30d: number;
  cpl_30d: number | null;
  reason: string;
}

interface BudgetRow {
  Platform: string;
  "Campaign/Tactic": string;
  "Current Spend": string;
  "Recommended Spend": string;
  "Delta (%)": string;
  Reasoning: string;
}

interface EmailReport {
  subject: string;
  body: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

// ─────────────────────────────────────────────────────────────────────────────
// Plain-text email converter
// Strips all markdown and renders structured blocks as clean, copy-paste-ready text
// ─────────────────────────────────────────────────────────────────────────────

function convertToEmailText(content: string): string {
  const lines = content.split("\n");
  const out: string[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    // ── Special code blocks ─────────────────────────────────────────────────
    if (trimmed.startsWith("```")) {
      const blockType = trimmed.replace(/```/g, "").trim().toLowerCase();
      const blockLines: string[] = [];
      let j = i + 1;
      while (j < lines.length && !lines[j].trim().startsWith("```")) {
        blockLines.push(lines[j]);
        j++;
      }
      const rawContent = blockLines.join("\n").trim();

      if (blockType === "email_report") {
        // Already plain text — inject directly
        out.push(rawContent);
        i = j + 1;
        continue;
      }

      if (blockType === "pause_list") {
        try {
          const items: PauseItem[] = JSON.parse(rawContent);
          out.push("PAUSE RECOMMENDATIONS");
          out.push("─".repeat(50));
          items.forEach((item, idx) => {
            const cpl = item.cpl_30d ? `  CPL: $${item.cpl_30d.toFixed(2)}` : "";
            const age = item.days_running !== null ? `  Running: ${item.days_running}d` : "";
            out.push(`${idx + 1}. ${item.ad_name}`);
            out.push(`   Campaign: ${item.campaign}`);
            out.push(`   Ad Set: ${item.adset}`);
            out.push(`   Spend: $${item.spend_30d.toFixed(2)}  Leads: ${item.leads_30d}${cpl}${age}`);
            out.push(`   Reason: ${item.reason}`);
            out.push("");
          });
          i = j + 1;
          continue;
        } catch { /* fall through */ }
      }

      if (blockType === "budget_table") {
        try {
          const rows: BudgetRow[] = JSON.parse(rawContent);
          out.push("BUDGET ALLOCATION");
          out.push("─".repeat(50));
          rows.forEach((row) => {
            out.push(`• ${row["Campaign/Tactic"]} (${row.Platform})`);
            out.push(`  Current: ${row["Current Spend"]}  →  Recommended: ${row["Recommended Spend"]}  (${row["Delta (%)"]})`);
            out.push(`  ${row.Reasoning}`);
            out.push("");
          });
          i = j + 1;
          continue;
        } catch { /* fall through */ }
      }

      // Other code blocks — skip entirely in email text
      i = j + 1;
      continue;
    }

    // ── Headers → UPPERCASE labels ──────────────────────────────────────────
    if (trimmed.startsWith("## ")) {
      const text = trimmed.slice(3).replace(/\*\*/g, "");
      out.push("");
      out.push(text.toUpperCase());
      out.push("─".repeat(Math.min(text.length + 4, 50)));
      i++; continue;
    }
    if (trimmed.startsWith("### ")) {
      const text = trimmed.slice(4).replace(/\*\*/g, "");
      out.push("");
      out.push(text);
      i++; continue;
    }
    if (trimmed.startsWith("# ")) {
      const text = trimmed.slice(2).replace(/\*\*/g, "");
      out.push(text.toUpperCase());
      out.push("═".repeat(Math.min(text.length + 4, 60)));
      i++; continue;
    }

    // ── Lists ───────────────────────────────────────────────────────────────
    const ulMatch = trimmed.match(/^[-*•]\s+(.+)/);
    if (ulMatch) {
      out.push(`• ${stripInlineMarkdown(ulMatch[1])}`);
      i++; continue;
    }
    const olMatch = trimmed.match(/^(\d+)\.\s+(.+)/);
    if (olMatch) {
      out.push(`${olMatch[1]}. ${stripInlineMarkdown(olMatch[2])}`);
      i++; continue;
    }

    // ── Horizontal rules → blank line ───────────────────────────────────────
    if (trimmed.match(/^[-*_]{3,}$/)) {
      out.push("");
      i++; continue;
    }

    // ── Regular text ────────────────────────────────────────────────────────
    if (trimmed) {
      out.push(stripInlineMarkdown(trimmed));
    } else {
      out.push("");
    }
    i++;
  }

  // Collapse 3+ consecutive blank lines to 2
  const collapsed = out.join("\n").replace(/\n{3,}/g, "\n\n");
  return collapsed.trim();
}

function stripInlineMarkdown(text: string): string {
  return text
    .replace(/\*\*(.+?)\*\*/g, "$1")   // bold
    .replace(/\*(.+?)\*/g, "$1")        // italic
    .replace(/`([^`]+)`/g, "$1")        // inline code
    .replace(/\[(.+?)\]\(.+?\)/g, "$1") // links
    .trim();
}

// ─────────────────────────────────────────────────────────────────────────────
// Copy-for-email button — appears on hover over every Jarvis message
// ─────────────────────────────────────────────────────────────────────────────

function CopyEmailButton({ content }: { content: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    const emailText = convertToEmailText(content);
    try {
      await navigator.clipboard.writeText(emailText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for older browsers
      const el = document.createElement("textarea");
      el.value = emailText;
      el.style.position = "fixed";
      el.style.opacity = "0";
      document.body.appendChild(el);
      el.select();
      document.execCommand("copy");
      document.body.removeChild(el);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [content]);

  return (
    <button
      onClick={handleCopy}
      title="Copy as plain text for email"
      className={cn(
        "flex items-center gap-1.5 text-xs px-2 py-1 rounded transition-all duration-150",
        copied
          ? "text-green-600 dark:text-green-400 bg-green-500/10"
          : "text-muted-foreground hover:text-foreground hover:bg-muted"
      )}
    >
      {copied ? (
        <><Check className="h-3 w-3" /><span>Copied!</span></>
      ) : (
        <><Copy className="h-3 w-3" /><span>Copy for email</span></>
      )}
    </button>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// email_report block renderer — subject line + body, clean visual treatment
// ─────────────────────────────────────────────────────────────────────────────

function EmailReportBlock({ content }: { content: string }) {
  const [copied, setCopied] = useState(false);

  // Parse optional subject line: first line starting with "Subject:" or "SUBJECT:"
  const lines = content.trim().split("\n");
  let subject = "";
  let body = content.trim();

  if (lines[0].match(/^subject:/i)) {
    subject = lines[0].replace(/^subject:\s*/i, "").trim();
    body = lines.slice(1).join("\n").trim();
  }

  const handleCopy = useCallback(async () => {
    const full = subject ? `Subject: ${subject}\n\n${body}` : body;
    try {
      await navigator.clipboard.writeText(full);
    } catch {
      const el = document.createElement("textarea");
      el.value = full;
      el.style.position = "fixed";
      el.style.opacity = "0";
      document.body.appendChild(el);
      el.select();
      document.execCommand("copy");
      document.body.removeChild(el);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [subject, body]);

  return (
    <div className="my-4 rounded-lg border border-blue-200 dark:border-blue-800 bg-blue-50/50 dark:bg-blue-950/20 overflow-hidden">
      {/* Header bar */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-blue-100/60 dark:bg-blue-900/30 border-b border-blue-200 dark:border-blue-800">
        <div className="flex items-center gap-2">
          <Mail className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" />
          <span className="text-xs font-semibold text-blue-700 dark:text-blue-300">Client Email Report</span>
        </div>
        <button
          onClick={handleCopy}
          className={cn(
            "flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-md font-medium transition-all",
            copied
              ? "bg-green-500 text-white"
              : "bg-blue-600 hover:bg-blue-700 text-white"
          )}
        >
          {copied ? <><Check className="h-3 w-3" /> Copied!</> : <><Copy className="h-3 w-3" /> Copy</>}
        </button>
      </div>

      {/* Subject line */}
      {subject && (
        <div className="px-4 py-2 border-b border-blue-200 dark:border-blue-800 bg-white/40 dark:bg-black/10">
          <span className="text-xs text-blue-600 dark:text-blue-400 font-medium">Subject: </span>
          <span className="text-xs font-semibold text-foreground">{subject}</span>
        </div>
      )}

      {/* Body — plain text, monospace feel but readable */}
      <div className="px-4 py-3">
        <pre className="text-sm leading-relaxed whitespace-pre-wrap font-sans text-foreground">
          {body}
        </pre>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Pause list renderer
// ─────────────────────────────────────────────────────────────────────────────

function PauseListBlock({ items }: { items: PauseItem[] }) {
  return (
    <div className="my-4 space-y-3">
      <div className="flex items-center gap-2 text-sm font-semibold text-foreground mb-3">
        <PauseCircle className="h-4 w-4 text-orange-500" />
        <span>Pause Recommendations — {items.length} ad{items.length !== 1 ? "s" : ""}</span>
      </div>
      {items.map((item, idx) => {
        const hasSpend = item.spend_30d > 0;
        const hasLeads = item.leads_30d > 0;
        const isZeroActivity = !hasSpend && !hasLeads;
        return (
          <div key={idx} className="rounded-lg border border-border bg-background p-4 space-y-2">
            <div className="flex items-start gap-2">
              <span className="flex-shrink-0 h-5 w-5 rounded-full bg-orange-500/10 text-orange-500 text-xs font-bold flex items-center justify-center mt-0.5">
                {idx + 1}
              </span>
              <p className="text-sm font-semibold text-foreground leading-tight">{item.ad_name}</p>
            </div>
            <div className="pl-7 space-y-0.5">
              <p className="text-xs text-muted-foreground">
                <span className="font-medium text-foreground/70">Campaign:</span> {item.campaign}
              </p>
              <p className="text-xs text-muted-foreground">
                <span className="font-medium text-foreground/70">Ad Set:</span> {item.adset}
              </p>
            </div>
            <div className="pl-7 flex flex-wrap gap-3 text-xs">
              {item.days_running !== null && (
                <span className="text-muted-foreground">
                  <span className="font-medium text-foreground/70">Running:</span> {item.days_running}d
                </span>
              )}
              <span className={cn("font-medium", hasSpend ? "text-foreground" : "text-muted-foreground")}>
                <span className="font-medium text-foreground/70">Spend:</span>{" "}
                ${item.spend_30d.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
              <span className={cn("font-medium", hasLeads ? "text-green-600 dark:text-green-400" : "text-muted-foreground")}>
                <span className="font-medium text-foreground/70">Leads:</span> {item.leads_30d}
              </span>
              {item.cpl_30d !== null && item.cpl_30d > 0 && (
                <span className="text-muted-foreground">
                  <span className="font-medium text-foreground/70">CPL:</span> ${item.cpl_30d.toFixed(2)}
                </span>
              )}
              {isZeroActivity && (
                <span className="text-xs text-muted-foreground italic">No activity in window</span>
              )}
            </div>
            <div className="pl-7">
              <p className="text-xs text-orange-600 dark:text-orange-400 flex items-start gap-1.5">
                <AlertCircle className="h-3 w-3 flex-shrink-0 mt-0.5" />
                {item.reason}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Budget table renderer
// ─────────────────────────────────────────────────────────────────────────────

function BudgetTableBlock({ rows }: { rows: BudgetRow[] }) {
  return (
    <div className="my-4 space-y-3">
      <div className="flex items-center gap-2 text-sm font-semibold text-foreground mb-3">
        <TrendingUp className="h-4 w-4 text-blue-500" />
        <span>Budget Allocation Recommendations</span>
      </div>
      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-muted/60 border-b border-border">
              <th className="px-3 py-2 text-left font-semibold">Campaign / Tactic</th>
              <th className="px-3 py-2 text-right font-semibold whitespace-nowrap">Current</th>
              <th className="px-3 py-2 text-right font-semibold whitespace-nowrap">Recommended</th>
              <th className="px-3 py-2 text-right font-semibold whitespace-nowrap">Delta</th>
              <th className="px-3 py-2 text-left font-semibold">Reasoning</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => {
              const delta = row["Delta (%)"] || "";
              const isPositive = delta.startsWith("+");
              const isNegative = delta.startsWith("-");
              return (
                <tr key={idx} className="border-b border-border/50 hover:bg-muted/30 transition-colors">
                  <td className="px-3 py-2">
                    <div className="font-medium text-foreground">{row["Campaign/Tactic"]}</div>
                    {row.Platform && <div className="text-muted-foreground text-[10px]">{row.Platform}</div>}
                  </td>
                  <td className="px-3 py-2 text-right text-muted-foreground whitespace-nowrap">{row["Current Spend"]}</td>
                  <td className="px-3 py-2 text-right font-medium text-foreground whitespace-nowrap">{row["Recommended Spend"]}</td>
                  <td className={cn(
                    "px-3 py-2 text-right font-semibold whitespace-nowrap",
                    isPositive ? "text-green-600 dark:text-green-400" :
                    isNegative ? "text-red-500 dark:text-red-400" :
                    "text-muted-foreground"
                  )}>{delta}</td>
                  <td className="px-3 py-2 text-muted-foreground leading-relaxed max-w-[240px]">{row.Reasoning}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Inline text formatting
// ─────────────────────────────────────────────────────────────────────────────

function parseInlineFormatting(text: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  let remaining = text;
  let key = 0;

  while (remaining.length > 0) {
    const boldMatch = remaining.match(/\*\*(.+?)\*\*/);
    const italicMatch = remaining.match(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/);
    const codeMatch = remaining.match(/`([^`]+)`/);

    const matches = [
      boldMatch ? { type: "bold", match: boldMatch, index: boldMatch.index! } : null,
      italicMatch ? { type: "italic", match: italicMatch, index: italicMatch.index! } : null,
      codeMatch ? { type: "code", match: codeMatch, index: codeMatch.index! } : null,
    ].filter(Boolean).sort((a, b) => a!.index - b!.index);

    if (matches.length === 0) { parts.push(<span key={key++}>{remaining}</span>); break; }

    const first = matches[0]!;
    if (first.index > 0) parts.push(<span key={key++}>{remaining.slice(0, first.index)}</span>);

    if (first.type === "bold") {
      parts.push(<strong key={key++} className="font-semibold">{first.match[1]}</strong>);
    } else if (first.type === "italic") {
      parts.push(<em key={key++}>{first.match[1]}</em>);
    } else if (first.type === "code") {
      parts.push(
        <code key={key++} className="bg-muted-foreground/10 px-1.5 py-0.5 rounded text-[13px] font-mono">
          {first.match[1]}
        </code>
      );
    }
    remaining = remaining.slice(first.index + first.match[0].length);
  }
  return parts;
}

// ─────────────────────────────────────────────────────────────────────────────
// Markdown table renderer
// ─────────────────────────────────────────────────────────────────────────────

function parseTable(lines: string[], startIndex: number): { element: React.ReactNode; endIndex: number } {
  const tableLines: string[] = [];
  let i = startIndex;
  while (i < lines.length && (lines[i].includes("|") || lines[i].match(/^[\s\-|:]+$/))) {
    tableLines.push(lines[i]);
    i++;
  }
  if (tableLines.length < 2) return { element: null, endIndex: startIndex };

  const headers = tableLines[0].split("|").map(h => h.trim()).filter(Boolean);
  const rows = tableLines.slice(2)
    .map(line => line.split("|").map(cell => cell.trim()).filter(Boolean))
    .filter(row => row.length > 0);

  const element = (
    <div key={`table-${startIndex}`} className="my-4 overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-xs">
        <thead>
          <tr className="bg-muted/60 border-b border-border">
            {headers.map((header, idx) => (
              <th key={idx} className="px-3 py-2 text-left font-semibold">{header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIdx) => (
            <tr key={rowIdx} className="border-b border-border/50 hover:bg-muted/30">
              {row.map((cell, cellIdx) => (
                <td key={cellIdx} className="px-3 py-2">{parseInlineFormatting(cell)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
  return { element, endIndex: i - 1 };
}

// ─────────────────────────────────────────────────────────────────────────────
// Code block renderer (fallback)
// ─────────────────────────────────────────────────────────────────────────────

function parseCodeBlock(lines: string[], startIndex: number): { element: React.ReactNode; endIndex: number } {
  const language = lines[startIndex].replace(/```/g, "").trim();
  const codeLines: string[] = [];
  let i = startIndex + 1;
  while (i < lines.length && !lines[i].startsWith("```")) {
    codeLines.push(lines[i]);
    i++;
  }
  const element = (
    <div key={`code-${startIndex}`} className="my-4">
      {language && (
        <div className="bg-muted/80 px-3 py-1 text-xs font-mono text-muted-foreground rounded-t-lg border border-b-0 border-border">
          {language}
        </div>
      )}
      <pre className={cn(
        "bg-muted/50 p-4 overflow-x-auto text-sm font-mono border border-border",
        language ? "rounded-b-lg" : "rounded-lg"
      )}>
        <code>{codeLines.join("\n")}</code>
      </pre>
    </div>
  );
  return { element, endIndex: i };
}

// ─────────────────────────────────────────────────────────────────────────────
// Main message formatter
// ─────────────────────────────────────────────────────────────────────────────

function formatMessage(content: string): React.ReactNode {
  const lines = content.split("\n");
  const elements: React.ReactNode[] = [];
  let i = 0;
  let listItems: React.ReactNode[] = [];
  let listType: "ul" | "ol" | null = null;

  const flushList = () => {
    if (listItems.length === 0) return;
    elements.push(
      listType === "ul"
        ? <ul key={`list-${elements.length}`} className="my-2 ml-4 space-y-1 list-disc">{listItems}</ul>
        : <ol key={`list-${elements.length}`} className="my-2 ml-4 space-y-1 list-decimal">{listItems}</ol>
    );
    listItems = [];
    listType = null;
  };

  while (i < lines.length) {
    const line = lines[i];
    const trimmedLine = line.trim();

    // ── Special code blocks ─────────────────────────────────────────────────
    if (trimmedLine.startsWith("```")) {
      flushList();
      const blockType = trimmedLine.replace(/```/g, "").trim().toLowerCase();
      const blockLines: string[] = [];
      let j = i + 1;
      while (j < lines.length && !lines[j].trim().startsWith("```")) {
        blockLines.push(lines[j]);
        j++;
      }
      const rawContent = blockLines.join("\n").trim();

      if (blockType === "email_report") {
        elements.push(<EmailReportBlock key={`email-${i}`} content={rawContent} />);
        i = j + 1; continue;
      }
      if (blockType === "pause_list") {
        try {
          const items: PauseItem[] = JSON.parse(rawContent);
          elements.push(<PauseListBlock key={`pause-${i}`} items={items} />);
          i = j + 1; continue;
        } catch { /* fall through */ }
      }
      if (blockType === "budget_table") {
        try {
          const rows: BudgetRow[] = JSON.parse(rawContent);
          elements.push(<BudgetTableBlock key={`budget-${i}`} rows={rows} />);
          i = j + 1; continue;
        } catch { /* fall through */ }
      }

      const { element, endIndex } = parseCodeBlock(lines, i);
      elements.push(element);
      i = endIndex + 1; continue;
    }

    // ── Markdown table ──────────────────────────────────────────────────────
    if (trimmedLine.includes("|") && i + 1 < lines.length && lines[i + 1].match(/^[\s\-|:]+$/)) {
      flushList();
      const { element, endIndex } = parseTable(lines, i);
      if (element) { elements.push(element); i = endIndex + 1; continue; }
    }

    // ── Headers ─────────────────────────────────────────────────────────────
    if (trimmedLine.startsWith("### ")) {
      flushList();
      elements.push(<h3 key={i} className="text-sm font-bold mt-5 mb-1.5 text-foreground tracking-tight">{parseInlineFormatting(trimmedLine.slice(4))}</h3>);
      i++; continue;
    }
    if (trimmedLine.startsWith("## ")) {
      flushList();
      elements.push(<h2 key={i} className="text-base font-bold mt-5 mb-2 text-foreground border-b border-border pb-1.5">{parseInlineFormatting(trimmedLine.slice(3))}</h2>);
      i++; continue;
    }
    if (trimmedLine.startsWith("# ")) {
      flushList();
      elements.push(<h1 key={i} className="text-lg font-bold mt-5 mb-2 text-foreground">{parseInlineFormatting(trimmedLine.slice(2))}</h1>);
      i++; continue;
    }

    // ── HR ───────────────────────────────────────────────────────────────────
    if (trimmedLine.match(/^[-*_]{3,}$/)) {
      flushList();
      elements.push(<hr key={i} className="my-4 border-border" />);
      i++; continue;
    }

    // ── Lists ────────────────────────────────────────────────────────────────
    if (trimmedLine.match(/^[-*•]\s+/)) {
      if (listType !== "ul") { flushList(); listType = "ul"; }
      listItems.push(<li key={`li-${i}`} className="text-sm leading-relaxed">{parseInlineFormatting(trimmedLine.replace(/^[-*•]\s+/, ""))}</li>);
      i++; continue;
    }
    if (trimmedLine.match(/^\d+\.\s+/)) {
      if (listType !== "ol") { flushList(); listType = "ol"; }
      listItems.push(<li key={`li-${i}`} className="text-sm leading-relaxed">{parseInlineFormatting(trimmedLine.replace(/^\d+\.\s+/, ""))}</li>);
      i++; continue;
    }

    // ── Empty line ───────────────────────────────────────────────────────────
    if (!trimmedLine) {
      flushList();
      const lastEl = elements[elements.length - 1];
      if (elements.length > 0 && (lastEl as React.ReactElement)?.key !== `space-${i - 1}`) {
        elements.push(<div key={`space-${i}`} className="h-1.5" />);
      }
      i++; continue;
    }

    // ── Paragraph ────────────────────────────────────────────────────────────
    flushList();
    elements.push(<p key={i} className="text-sm leading-relaxed">{parseInlineFormatting(trimmedLine)}</p>);
    i++;
  }

  flushList();
  return <div className="space-y-0.5">{elements}</div>;
}

// ─────────────────────────────────────────────────────────────────────────────
// Main JarvisChat component
// ─────────────────────────────────────────────────────────────────────────────

export function JarvisChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId] = useState(() => `web-${Date.now()}`);
  const [hoveredMessageId, setHoveredMessageId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async (overrideText?: string) => {
    const text = (overrideText ?? input).trim();
    if (!text || isLoading) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content: text,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE}/api/chat/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, session_id: sessionId }),
      });

      if (!response.ok) throw new Error("Failed to get response");

      const data = await response.json();
      setMessages((prev) => [...prev, {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: data.response,
        timestamp: new Date(),
        dataSource: data.data_source,
      }]);
    } catch {
      setMessages((prev) => [...prev, {
        id: `error-${Date.now()}`,
        role: "assistant",
        content: "Sorry, I encountered an error. Please try again.",
        timestamp: new Date(),
      }]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const clearChat = async () => {
    try {
      await fetch(`${API_BASE}/api/chat/clear?session_id=${sessionId}`, { method: "POST" });
    } catch { /* ignore */ }
    setMessages([]);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const quickActions = [
    { emoji: "📊", text: "How did we perform last 7 days?" },
    { emoji: "⏸️", text: "Which campaigns should I pause?" },
    { emoji: "💰", text: "How should I reallocate the remaining budget?" },
    { emoji: "📧", text: "Write a client email report for MTD performance" },
  ];

  return (
    <Card className="flex flex-col h-[calc(100vh-8rem)]">
      <CardHeader className="border-b flex-shrink-0 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
              <Bot className="h-6 w-6 text-primary" />
            </div>
            <div>
              <CardTitle className="flex items-center gap-2">
                JARVIS
                <Sparkles className="h-4 w-4 text-yellow-500" />
              </CardTitle>
              <p className="text-sm text-muted-foreground">Paid Media Intelligence Assistant</p>
            </div>
          </div>
          {messages.length > 0 && (
            <Button variant="ghost" size="sm" onClick={clearChat} className="text-muted-foreground hover:text-destructive">
              <Trash2 className="h-4 w-4 mr-1" />
              Clear
            </Button>
          )}
        </div>
      </CardHeader>

      <CardContent className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center text-muted-foreground">
            <Bot className="h-16 w-16 mb-4 opacity-20" />
            <h3 className="text-lg font-medium mb-2">Welcome to JARVIS</h3>
            <p className="text-sm max-w-md">
              I&apos;m your AI-powered Paid Media Analyst. Ask me about campaign performance, budget allocation, or specific ad creatives.
            </p>
            <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-2 text-xs w-full max-w-sm">
              {quickActions.map(({ emoji, text }) => (
                <button
                  key={text}
                  onClick={() => sendMessage(text)}
                  className="px-3 py-2 rounded-lg bg-muted hover:bg-muted/80 transition-colors text-left"
                >
                  {emoji} {text}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={cn("flex gap-3", message.role === "user" ? "justify-end" : "justify-start")}
              onMouseEnter={() => message.role === "assistant" && setHoveredMessageId(message.id)}
              onMouseLeave={() => setHoveredMessageId(null)}
            >
              {message.role === "assistant" && (
                <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0 mt-1">
                  <Bot className="h-4 w-4 text-primary" />
                </div>
              )}

              <div className={cn(
                "rounded-lg max-w-[85%]",
                message.role === "user"
                  ? "bg-primary text-primary-foreground px-4 py-3"
                  : "bg-muted/50 border border-border px-5 py-4"
              )}>
                {message.role === "user" ? (
                  <p className="text-sm">{message.content}</p>
                ) : (
                  <>
                    <div className="text-foreground">
                      {formatMessage(message.content)}
                    </div>

                    {/* Action bar — copy button + data source */}
                    <div className={cn(
                      "flex items-center justify-between mt-3 pt-2 border-t border-border/40 transition-opacity duration-150",
                      hoveredMessageId === message.id ? "opacity-100" : "opacity-0"
                    )}>
                      <CopyEmailButton content={message.content} />
                      {message.dataSource && (
                        <p className="text-xs text-muted-foreground">
                          📊 {message.dataSource}
                        </p>
                      )}
                    </div>

                    {/* Always-visible data source when not hovered */}
                    {message.dataSource && hoveredMessageId !== message.id && (
                      <p className="text-xs mt-2 pt-2 border-t border-border/40 text-muted-foreground">
                        📊 {message.dataSource}
                      </p>
                    )}
                  </>
                )}
              </div>

              {message.role === "user" && (
                <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center flex-shrink-0 mt-1">
                  <User className="h-4 w-4 text-primary-foreground" />
                </div>
              )}
            </div>
          ))
        )}
        {isLoading && (
          <div className="flex gap-3">
            <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
              <Bot className="h-4 w-4 text-primary" />
            </div>
            <div className="bg-muted/50 border border-border rounded-lg px-5 py-4">
              <div className="flex items-center gap-2 text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span className="text-sm">Analyzing…</span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </CardContent>

      <div className="border-t p-4 flex-shrink-0 bg-background">
        <div className="flex gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask JARVIS about campaigns, specific ads, or budget — or request a client email report…"
            className="flex-1 resize-none rounded-lg border bg-background px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary min-h-[48px] max-h-[120px]"
            rows={1}
            disabled={isLoading}
          />
          <Button onClick={() => sendMessage()} disabled={!input.trim() || isLoading} size="lg" className="px-4">
            {isLoading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
          </Button>
        </div>
        <p className="text-xs text-muted-foreground mt-2 text-center">
          Enter to send · Shift+Enter for new line
        </p>
      </div>
    </Card>
  );
}
