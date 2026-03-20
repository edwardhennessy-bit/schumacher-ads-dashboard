"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Send, Bot, User, Loader2, Trash2, Sparkles, Copy, Check,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  formatMessage,
  type PauseItem,
  type BudgetRow,
} from "@/components/chat/JarvisMessageRenderer";

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

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

// ─────────────────────────────────────────────────────────────────────────────
// Plain-text email converter
// Strips all markdown and renders structured blocks as clean, copy-paste-ready text
// ─────────────────────────────────────────────────────────────────────────────

function stripInlineMarkdown(text: string): string {
  return text
    .replace(/\*\*(.+?)\*\*/g, "$1")   // bold
    .replace(/\*(.+?)\*/g, "$1")        // italic
    .replace(/`([^`]+)`/g, "$1")        // inline code
    .replace(/\[(.+?)\]\(.+?\)/g, "$1") // links
    .trim();
}

function convertToEmailText(content: string): string {
  const lines = content.split("\n");
  const out: string[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

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
        out.push(rawContent);
        i = j + 1; continue;
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
          i = j + 1; continue;
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
          i = j + 1; continue;
        } catch { /* fall through */ }
      }
      i = j + 1; continue;
    }

    if (trimmed.startsWith("## ")) {
      const text = trimmed.slice(3).replace(/\*\*/g, "");
      out.push(""); out.push(text.toUpperCase());
      out.push("─".repeat(Math.min(text.length + 4, 50)));
      i++; continue;
    }
    if (trimmed.startsWith("### ")) {
      const text = trimmed.slice(4).replace(/\*\*/g, "");
      out.push(""); out.push(text);
      i++; continue;
    }
    if (trimmed.startsWith("# ")) {
      const text = trimmed.slice(2).replace(/\*\*/g, "");
      out.push(text.toUpperCase());
      out.push("═".repeat(Math.min(text.length + 4, 60)));
      i++; continue;
    }

    const ulMatch = trimmed.match(/^[-*•]\s+(.+)/);
    if (ulMatch) { out.push(`• ${stripInlineMarkdown(ulMatch[1])}`); i++; continue; }
    const olMatch = trimmed.match(/^(\d+)\.\s+(.+)/);
    if (olMatch) { out.push(`${olMatch[1]}. ${stripInlineMarkdown(olMatch[2])}`); i++; continue; }

    if (trimmed.match(/^[-*_]{3,}$/)) { out.push(""); i++; continue; }

    if (trimmed) {
      out.push(stripInlineMarkdown(trimmed));
    } else {
      out.push("");
    }
    i++;
  }

  return out.join("\n").replace(/\n{3,}/g, "\n\n").trim();
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
                  className="px-3 py-2 rounded-lg bg-muted hover:bg-[#f27038]/10 hover:border-[#f27038]/30 border border-transparent transition-colors text-left"
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
