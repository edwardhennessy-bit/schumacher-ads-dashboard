"use client";

/**
 * JarvisMessageRenderer — shared markdown-to-React renderer used by
 * both JarvisChat (full page) and JarvisDrawer (slide-in panel).
 */

import React, { useState, useCallback } from "react";
import {
  PauseCircle, TrendingUp, AlertCircle, Copy, Check, Mail,
} from "lucide-react";

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

export interface PauseItem {
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

export interface BudgetRow {
  Platform: string;
  "Campaign/Tactic": string;
  "Current Spend": string;
  "Recommended Spend": string;
  "Delta (%)": string;
  Reasoning: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Utility — cn (no dep on lib/utils needed here)
// ─────────────────────────────────────────────────────────────────────────────

function cn(...classes: (string | boolean | undefined | null)[]) {
  return classes.filter(Boolean).join(" ");
}

// ─────────────────────────────────────────────────────────────────────────────
// email_report block renderer
// ─────────────────────────────────────────────────────────────────────────────

export function EmailReportBlock({ content }: { content: string }) {
  const [copied, setCopied] = useState(false);

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
    <div className="my-4 rounded-lg border border-[#f27038]/30 bg-[#f27038]/5 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2.5 bg-[#f27038]/10 border-b border-[#f27038]/20">
        <div className="flex items-center gap-2">
          <Mail className="h-3.5 w-3.5 text-[#f27038]" />
          <span className="text-xs font-semibold text-[#f27038]">Client Email Report</span>
        </div>
        <button
          onClick={handleCopy}
          className={cn(
            "flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-md font-medium transition-all",
            copied ? "bg-green-500 text-white" : "bg-[#f27038] hover:bg-[#d4612e] text-white"
          )}
        >
          {copied ? <><Check className="h-3 w-3" /> Copied!</> : <><Copy className="h-3 w-3" /> Copy</>}
        </button>
      </div>
      {subject && (
        <div className="px-4 py-2 border-b border-[#f27038]/20 bg-white/40">
          <span className="text-xs text-[#f27038] font-medium">Subject: </span>
          <span className="text-xs font-semibold text-foreground">{subject}</span>
        </div>
      )}
      <div className="px-4 py-3">
        <pre className="text-sm leading-relaxed whitespace-pre-wrap font-sans text-foreground">{body}</pre>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Pause list renderer
// ─────────────────────────────────────────────────────────────────────────────

export function PauseListBlock({ items }: { items: PauseItem[] }) {
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

export function BudgetTableBlock({ rows }: { rows: BudgetRow[] }) {
  return (
    <div className="my-4 space-y-3">
      <div className="flex items-center gap-2 text-sm font-semibold text-foreground mb-3">
        <TrendingUp className="h-4 w-4 text-[#f27038]" />
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

export function parseInlineFormatting(text: string): React.ReactNode[] {
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
// Main message formatter — parses markdown into rich React nodes
// ─────────────────────────────────────────────────────────────────────────────

export function formatMessage(content: string): React.ReactNode {
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
      elements.push(<h3 key={i} className="text-sm font-bold mt-4 mb-1.5 text-foreground tracking-tight">{parseInlineFormatting(trimmedLine.slice(4))}</h3>);
      i++; continue;
    }
    if (trimmedLine.startsWith("## ")) {
      flushList();
      elements.push(<h2 key={i} className="text-base font-bold mt-4 mb-2 text-foreground border-b border-border pb-1.5">{parseInlineFormatting(trimmedLine.slice(3))}</h2>);
      i++; continue;
    }
    if (trimmedLine.startsWith("# ")) {
      flushList();
      elements.push(<h1 key={i} className="text-lg font-bold mt-4 mb-2 text-foreground">{parseInlineFormatting(trimmedLine.slice(2))}</h1>);
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
