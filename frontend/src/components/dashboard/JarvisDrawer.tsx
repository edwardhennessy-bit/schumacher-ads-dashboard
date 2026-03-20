"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import {
  X, Maximize2, Minimize2, Send, Trash2, Clock, Calendar,
  Loader2, CheckCircle, Bot, Hash, Plus, ChevronDown, ChevronUp,
} from "lucide-react";
import { useJarvis, Section } from "@/context/JarvisContext";
import { api } from "@/lib/api";

// ── Section config ────────────────────────────────────────────────────────────

const SECTION_CONFIG: Record<Section, { label: string; color: string; emoji: string }> = {
  kpi_cards:      { label: "KPI Overview",     color: "orange", emoji: "📊" },
  active_ads:     { label: "Active Ads",        color: "orange", emoji: "📢" },
  trend_chart:    { label: "Trend Chart",       color: "orange", emoji: "📈" },
  campaign_table: { label: "Campaigns",         color: "orange", emoji: "🎯" },
  alerts:         { label: "Alerts",            color: "orange", emoji: "⚠️"  },
};

const SECTION_BADGE_CLASSES: Record<string, string> = {
  blue:   "bg-[#f27038]/10 text-[#f27038]",
  indigo: "bg-[#f27038]/10 text-[#f27038]",
  purple: "bg-[#f27038]/10 text-[#f27038]",
  violet: "bg-[#f27038]/10 text-[#f27038]",
  orange: "bg-[#f27038]/10 text-[#f27038]",
};

const SECTION_QUICK_PICKS: Record<Section, Array<{ label: string; prompt: string }>> = {
  kpi_cards: [
    { label: "Summarize KPIs",    prompt: "Give me a written summary of current KPI performance to share with the team." },
    { label: "Flag Concerns",     prompt: "Are there any KPIs that look unusual or concerning? Flag anything that needs attention." },
    { label: "CPL Analysis",      prompt: "Break down CPL performance — are we hitting our targets? Any campaigns driving it up?" },
    { label: "Spend Pacing",      prompt: "How is spend pacing this month? Are we on track to hit budget?" },
    { label: "Slack Overview",    prompt: "Write a concise performance overview to send to Slack right now." },
  ],
  active_ads: [
    { label: "Health Report",     prompt: "Give me a full active ads health report — top 5 and bottom 5 campaigns and ads with KPIs." },
    { label: "CPL Flags",         prompt: "Flag all campaigns and ads where CPL exceeds $70. What should we pause or optimize?" },
    { label: "Top Performers",    prompt: "Show me the top 5 campaigns and top 5 ads by performance." },
    { label: "Remarketing Dive",  prompt: "Deep dive on remarketing campaign performance vs prospecting — leads, CPL, efficiency." },
    { label: "Visit Campaigns",   prompt: "Analyze all Visit/TOF campaigns — CTR, CPC, and click efficiency." },
  ],
  trend_chart: [
    { label: "Trend Summary",     prompt: "Summarize the performance trends and highlight any significant changes or patterns." },
    { label: "Spot Anomalies",    prompt: "Are there any anomalies, unusual spikes, or drops in the trend data? What caused them?" },
    { label: "Period Comparison", prompt: "Compare this period's performance to the previous period. What improved? What declined?" },
    { label: "Slack Summary",     prompt: "Write a brief trend summary to send to the team on Slack." },
  ],
  campaign_table: [
    { label: "Top by Leads",      prompt: "Rank all campaigns by leads generated. Who are the top performers and why?" },
    { label: "CPL Efficiency",    prompt: "Which campaigns have the best CPL efficiency? Which are underperforming and should be reviewed?" },
    { label: "Spend Breakdown",   prompt: "Break down spend allocation across campaigns. Are we investing in the right places?" },
    { label: "Table to Slack",    prompt: "Send a formatted campaign performance summary to Slack." },
    { label: "Worst Performers",  prompt: "Which campaigns are the bottom performers? Should any be paused?" },
  ],
  alerts: [
    { label: "Explain Alerts",    prompt: "Explain each current alert and what it means for campaign performance." },
    { label: "Prioritize Issues", prompt: "Which alerts are most critical and need immediate attention?" },
    { label: "Action Plan",       prompt: "For each alert, what specific action should I take right now?" },
    { label: "Slack Alert Report",prompt: "Send a summary of current alerts and recommended actions to Slack." },
  ],
};

// ── Timezone config ───────────────────────────────────────────────────────────

const TIMEZONES = [
  { value: "America/New_York",    label: "ET — Eastern" },
  { value: "America/Chicago",     label: "CT — Central" },
  { value: "America/Denver",      label: "MT — Mountain" },
  { value: "America/Phoenix",     label: "MT — Mountain (no DST)" },
  { value: "America/Los_Angeles", label: "PT — Pacific" },
  { value: "America/Anchorage",   label: "AKT — Alaska" },
  { value: "Pacific/Honolulu",    label: "HST — Hawaii" },
  { value: "Europe/London",       label: "GMT/BST — London" },
  { value: "Europe/Paris",        label: "CET — Central Europe" },
  { value: "Asia/Dubai",          label: "GST — Dubai" },
  { value: "Asia/Kolkata",        label: "IST — India" },
  { value: "Asia/Singapore",      label: "SGT — Singapore" },
  { value: "Asia/Tokyo",          label: "JST — Tokyo" },
  { value: "Australia/Sydney",    label: "AEST — Sydney" },
  { value: "Pacific/Auckland",    label: "NZST — Auckland" },
];

const DAYS = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"];
const DAY_LABELS: Record<string, string> = { monday:"Monday", tuesday:"Tuesday", wednesday:"Wednesday", thursday:"Thursday", friday:"Friday", saturday:"Saturday", sunday:"Sunday" };
function formatHour(h: number) { if (h===0) return "12:00 AM"; if (h<12) return `${h}:00 AM`; if (h===12) return "12:00 PM"; return `${h-12}:00 PM`; }

// ── Main Drawer Content ───────────────────────────────────────────────────────

function DrawerContent({ expanded = false }: { expanded?: boolean }) {
  const {
    activeSection, threads, isTyping, sendMessage, clearThread,
    isExpanded, setIsExpanded, close,
    channels, setChannels, selectedChannel, setSelectedChannel,
    scheduleDay, scheduleHour, scheduleTimezone, scheduleSaveState,
    handleDayChange, handleHourChange, handleTimezoneChange, handleScheduleSave,
    slackSendState, handleSendToSlack,
  } = useJarvis();

  const [input, setInput] = useState("");
  const [showSchedule, setShowSchedule] = useState(false);
  const [showAddChannel, setShowAddChannel] = useState(false);
  const [newChannelName, setNewChannelName] = useState("");
  const [addingChannel, setAddingChannel] = useState(false);
  const [addChannelError, setAddChannelError] = useState("");

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const threadEndRef = useRef<HTMLDivElement>(null);

  const section = activeSection!;
  const config = SECTION_CONFIG[section];
  const messages = threads[section] || [];
  const quickPicks = SECTION_QUICK_PICKS[section];
  const hasLastAssistant = messages.some(m => m.role === "assistant");

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [input]);

  // Scroll to bottom on new messages
  useEffect(() => {
    threadEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const handleSend = async () => {
    const content = input.trim();
    if (!content || isTyping) return;
    setInput("");
    await sendMessage(content);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  const handleAddChannel = async () => {
    const ch = newChannelName.trim().replace(/^#/, "");
    if (!ch) return;
    setAddingChannel(true);
    setAddChannelError("");
    try {
      const res = await api.addSlackChannel(ch);
      if (res.success && res.channels) {
        setChannels(res.channels);
        setSelectedChannel(ch);
        setShowAddChannel(false);
        setNewChannelName("");
      } else {
        setAddChannelError(res.error || "Could not add channel");
      }
    } catch {
      setAddChannelError("Failed to save channel");
    } finally {
      setAddingChannel(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* ── Header ── */}
      <div className="bg-gradient-to-br from-[#1e1e1e] to-[#2a2a2a] px-4 py-3 shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-xl">🤖</span>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-white font-bold text-sm">JARVIS</span>
              <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${SECTION_BADGE_CLASSES[config.color]} shrink-0`}>
                {config.emoji} {config.label}
              </span>
            </div>
            <div className="text-gray-400 text-xs">AI-powered report assistant</div>
          </div>
          <div className="flex items-center gap-1 shrink-0">
            {messages.length > 0 && (
              <button onClick={() => clearThread(section)} title="Clear thread" className="text-gray-400 hover:text-white p-1.5 rounded hover:bg-white/10 transition-colors">
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            )}
            {!expanded && (
              <button onClick={() => setIsExpanded(true)} title="Expand" className="text-gray-400 hover:text-white p-1.5 rounded hover:bg-white/10 transition-colors">
                <Maximize2 className="h-3.5 w-3.5" />
              </button>
            )}
            {expanded && (
              <button onClick={() => setIsExpanded(false)} title="Collapse" className="text-gray-400 hover:text-white p-1.5 rounded hover:bg-white/10 transition-colors">
                <Minimize2 className="h-3.5 w-3.5" />
              </button>
            )}
            <button onClick={close} title="Close" className="text-gray-400 hover:text-white p-1.5 rounded hover:bg-white/10 transition-colors">
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* ── Quick picks ── */}
      <div className="px-3 py-2 border-b border-gray-100 bg-gray-50/50 shrink-0">
        <div className="flex gap-1.5 overflow-x-auto pb-0.5 scrollbar-none">
          {quickPicks.map((pick) => (
            <button
              key={pick.label}
              onClick={() => { setInput(pick.prompt); textareaRef.current?.focus(); }}
              className="text-xs px-2.5 py-1 rounded-full border border-gray-200 bg-white hover:bg-[#f27038]/10 hover:border-[#f27038]/30 hover:text-[#f27038] whitespace-nowrap transition-colors shrink-0"
            >
              {pick.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Chat thread ── */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center py-8">
            <div className="text-3xl mb-2">{config.emoji}</div>
            <p className="text-sm font-medium text-gray-600">Ask me anything about {config.label}</p>
            <p className="text-xs text-gray-400 mt-1">Use a quick pick above or type your own question</p>
          </div>
        )}
        {messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            {msg.role === "assistant" && (
              <div className="h-6 w-6 rounded-full bg-gradient-to-br from-[#f27038] to-[#d4612e] flex items-center justify-center shrink-0 mr-2 mt-0.5">
                <Bot className="h-3 w-3 text-white" />
              </div>
            )}
            <div className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm leading-relaxed whitespace-pre-wrap break-words ${
              msg.role === "user"
                ? "bg-[#f27038] text-white rounded-tr-sm"
                : "bg-white border border-gray-200 text-gray-800 shadow-sm rounded-tl-sm"
            }`}>
              {msg.content}
            </div>
          </div>
        ))}
        {isTyping && (
          <div className="flex justify-start">
            <div className="h-6 w-6 rounded-full bg-gradient-to-br from-[#f27038] to-[#d4612e] flex items-center justify-center shrink-0 mr-2 mt-0.5">
              <Bot className="h-3 w-3 text-white" />
            </div>
            <div className="bg-white border border-gray-200 shadow-sm rounded-2xl rounded-tl-sm px-3 py-2">
              <div className="flex gap-1 items-center h-4">
                <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
            </div>
          </div>
        )}
        <div ref={threadEndRef} />
      </div>

      {/* ── Input area ── */}
      <div className="px-3 py-2 border-t border-gray-100 shrink-0">
        <div className="flex gap-2 items-end">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask JARVIS anything… (Shift+Enter for new line)"
            rows={1}
            className="flex-1 text-sm border border-gray-200 rounded-xl px-3 py-2 resize-none overflow-hidden focus:ring-2 focus:ring-[#f27038]/50 focus:border-[#f27038]/50 outline-none leading-relaxed"
            style={{ maxHeight: "160px" }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isTyping}
            className="bg-[#f27038] hover:bg-[#d4612e] disabled:opacity-40 text-white rounded-xl p-2.5 transition-colors shrink-0 mb-0.5"
          >
            {isTyping ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {/* ── Send to Slack ── */}
      <div className="border-t border-gray-100 px-3 py-2.5 shrink-0">
        <div className="flex items-center gap-2 mb-2">
          <Hash className="h-3 w-3 text-gray-400" />
          <span className="text-xs text-gray-500 font-medium">Sending to</span>
          <span className="text-xs font-semibold text-[#f27038]">#{selectedChannel}</span>
          <span className="text-xs text-gray-400 ml-auto">(change in schedule ↓)</span>
        </div>
        <button
          onClick={handleSendToSlack}
          disabled={!hasLastAssistant || slackSendState === "sending"}
          className={`w-full text-sm rounded-lg px-4 py-2 font-medium flex items-center justify-center gap-2 transition-colors
            ${slackSendState === "sent" ? "bg-green-600 text-white" : slackSendState === "error" ? "bg-red-100 text-red-700 border border-red-300" : "bg-[#f27038] hover:bg-[#d4612e] text-white disabled:opacity-40"}`}
        >
          {slackSendState === "sending" ? <><Loader2 className="h-3.5 w-3.5 animate-spin" />Sending…</>
           : slackSendState === "sent" ? <><CheckCircle className="h-3.5 w-3.5" />Sent to Slack!</>
           : slackSendState === "error" ? <>Failed — try again</>
           : <><Send className="h-3.5 w-3.5" />Send Response to Slack</>}
        </button>
      </div>

      {/* ── Auto-schedule ── */}
      <div className="border-t border-gray-100 shrink-0">
        <button
          onClick={() => setShowSchedule(v => !v)}
          className="w-full flex items-center gap-2 px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wide hover:bg-gray-50 transition-colors"
        >
          <Clock className="h-3 w-3" />
          Auto-schedule
          {showSchedule ? <ChevronUp className="h-3 w-3 ml-auto" /> : <ChevronDown className="h-3 w-3 ml-auto" />}
        </button>
        {showSchedule && (
          <div className="px-3 pb-3 space-y-2">
            <div className="flex gap-2">
              <select value={scheduleDay} onChange={(e) => handleDayChange(e.target.value)} className="text-sm border border-gray-200 rounded-lg p-2 flex-1 focus:ring-2 focus:ring-[#f27038]/50 outline-none bg-white">
                {DAYS.map(d => <option key={d} value={d}>{DAY_LABELS[d]}</option>)}
              </select>
              <select value={scheduleHour} onChange={(e) => handleHourChange(Number(e.target.value))} className="text-sm border border-gray-200 rounded-lg p-2 flex-1 focus:ring-2 focus:ring-[#f27038]/50 outline-none bg-white">
                {Array.from({ length: 24 }, (_, i) => <option key={i} value={i}>{formatHour(i)}</option>)}
              </select>
            </div>
            <select value={scheduleTimezone} onChange={(e) => handleTimezoneChange(e.target.value)} className="text-sm border border-gray-200 rounded-lg p-2 w-full focus:ring-2 focus:ring-[#f27038]/50 outline-none bg-white">
              {TIMEZONES.map(tz => <option key={tz.value} value={tz.value}>{tz.label}</option>)}
            </select>
            <button
              onClick={handleScheduleSave}
              disabled={scheduleSaveState === "saving"}
              className={`w-full text-sm rounded-lg px-4 py-2 font-medium flex items-center justify-center gap-2 transition-colors border
                ${scheduleSaveState === "saved" ? "border-green-300 bg-green-50 text-green-700"
                  : scheduleSaveState === "error" ? "border-red-300 bg-red-50 text-red-700"
                  : "border-[#f27038]/50 text-[#f27038] hover:bg-[#f27038]/5 disabled:opacity-50"}`}
            >
              {scheduleSaveState === "saving" ? <><Loader2 className="h-3.5 w-3.5 animate-spin" />Saving…</>
               : scheduleSaveState === "saved" ? <><CheckCircle className="h-3.5 w-3.5" />Schedule saved!</>
               : scheduleSaveState === "error" ? <>Failed — try again</>
               : <><Calendar className="h-3.5 w-3.5" />Set Schedule</>}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Ask JARVIS button (used in section headers) ───────────────────────────────

export function AskJarvisButton({ section }: { section: Section }) {
  const { openForSection } = useJarvis();
  return (
    <button
      onClick={() => openForSection(section)}
      className="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg bg-[#f27038]/10 hover:bg-[#f27038]/20 text-[#f27038] border border-[#f27038]/30 transition-colors"
    >
      <Bot className="h-3.5 w-3.5" />
      Ask JARVIS
    </button>
  );
}

// ── Main Drawer component ─────────────────────────────────────────────────────

export function JarvisDrawer() {
  const { isOpen, activeSection, isExpanded, setIsExpanded, close, openForSection } = useJarvis();

  // Escape key closes
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") { if (isExpanded) setIsExpanded(false); else close(); } };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [isExpanded, setIsExpanded, close]);

  // Lock body scroll when modal open
  useEffect(() => {
    document.body.style.overflow = isExpanded ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [isExpanded]);

  return (
    <>
      {/* Floating toggle button — always visible when drawer is closed */}
      {!isOpen && (
        <button
          onClick={() => openForSection(activeSection || "kpi_cards")}
          className="fixed bottom-8 right-8 z-30 bg-gradient-to-br from-[#f27038] to-[#d4612e] text-white rounded-full w-14 h-14 flex items-center justify-center shadow-lg hover:shadow-xl hover:scale-105 transition-all"
          title="Open JARVIS"
        >
          <span className="text-xl">🤖</span>
        </button>
      )}

      {/* ── Sliding drawer ── */}
      <div
        className={`fixed top-0 right-0 h-full z-40 w-96 bg-white shadow-2xl border-l border-gray-200 flex flex-col transition-transform duration-300 ease-in-out ${
          isOpen && !isExpanded ? "translate-x-0" : "translate-x-full"
        }`}
      >
        {activeSection && <DrawerContent expanded={false} />}
      </div>

      {/* ── Full-screen modal ── */}
      {isExpanded && activeSection && typeof window !== "undefined" && createPortal(
        <div className="fixed inset-0 z-50 flex items-center justify-center p-6" onClick={(e) => { if (e.target === e.currentTarget) setIsExpanded(false); }}>
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" />
          <div className="relative z-10 bg-white rounded-2xl shadow-2xl w-full max-w-2xl h-[90vh] flex flex-col overflow-hidden">
            <DrawerContent expanded={true} />
          </div>
        </div>,
        document.body
      )}
    </>
  );
}
