"use client";

import { useState, useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { Send, Clock, Calendar, Loader2, CheckCircle, Maximize2, Minimize2, X, Plus, Hash, Info } from "lucide-react";
import { api } from "@/lib/api";

interface JarvisSidebarProps {
  startDate: string;
  endDate: string;
}

const QUICK_PICKS = [
  {
    label: "Top 5 by Leads",
    prompt:
      "Show me the top 5 campaigns and ads ranked by leads generated, with CPL analysis for each.",
  },
  {
    label: "Remarketing Deep Dive",
    prompt:
      "Give me a deep dive on remarketing campaign performance — leads, CPL, and efficiency compared to prospecting.",
  },
  {
    label: "Visit Campaign Efficiency",
    prompt:
      "Analyze all Visit/TOF campaigns and report on click efficiency, CTR, and CPC performance.",
  },
  {
    label: "CPL Alerts Only",
    prompt:
      "Flag all campaigns and ads where CPL exceeds $70 and suggest which to pause or optimize.",
  },
  {
    label: "Prospecting Only",
    prompt:
      "Focus exclusively on prospecting campaigns. Show top and bottom performers by leads and CPL.",
  },
  {
    label: "Full Health Report",
    prompt:
      "Give me the complete active ads health report — top 5 and bottom 5 campaigns, top 5 and bottom 5 ads, with all KPIs.",
  },
];

const DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];
const DAY_LABELS: Record<string, string> = {
  monday: "Monday",
  tuesday: "Tuesday",
  wednesday: "Wednesday",
  thursday: "Thursday",
  friday: "Friday",
  saturday: "Saturday",
  sunday: "Sunday",
};

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

/** Detect the browser's local timezone, falling back to ET */
function detectTimezone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "America/New_York";
  } catch {
    return "America/New_York";
  }
}

function formatHour(h: number): string {
  if (h === 0) return "12:00 AM";
  if (h < 12) return `${h}:00 AM`;
  if (h === 12) return "12:00 PM";
  return `${h - 12}:00 PM`;
}

/** Auto-resize a textarea to fit its content */
function useAutoResize(value: string) {
  const ref = useRef<HTMLTextAreaElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }, [value]);
  return ref;
}

// ---------------------------------------------------------------------------
// Shared form content — rendered identically in sidebar and modal
// ---------------------------------------------------------------------------

interface JarvisFormProps {
  prompt: string;
  setPrompt: (v: string) => void;
  channels: string[];
  setChannels: (chs: string[]) => void;
  selectedChannel: string;
  setSelectedChannel: (v: string) => void;
  scheduleDay: string;
  scheduleHour: number;
  scheduleTimezone: string;
  scheduleSaveState: "idle" | "saving" | "saved" | "error";
  isSending: boolean;
  sendState: "idle" | "success" | "error";
  sendMessage: string;
  handleDayChange: (d: string) => void;
  handleHourChange: (h: number) => void;
  handleTimezoneChange: (tz: string) => void;
  handleScheduleSave: () => void;
  handleSend: () => void;
  expanded?: boolean; // true = modal view
}

function JarvisForm({
  prompt,
  setPrompt,
  channels,
  setChannels,
  selectedChannel,
  setSelectedChannel,
  scheduleDay,
  scheduleHour,
  scheduleTimezone,
  scheduleSaveState,
  isSending,
  sendState,
  sendMessage,
  handleDayChange,
  handleHourChange,
  handleTimezoneChange,
  handleScheduleSave,
  handleSend,
  expanded = false,
}: JarvisFormProps) {
  const textareaRef = useAutoResize(prompt);
  const gridCols = expanded ? "grid-cols-3" : "grid-cols-2";

  // "Add to channel" state
  const [showAddChannel, setShowAddChannel] = useState(false);
  const [newChannelName, setNewChannelName] = useState("");
  const [addingChannel, setAddingChannel] = useState(false);
  const [addChannelError, setAddChannelError] = useState("");

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
    <div className={`flex flex-col flex-1 min-h-0 ${expanded ? "gap-5" : "gap-4"}`}>
      {/* Quick picks */}
      <div>
        <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
          Quick report
        </div>
        <div className={`grid ${gridCols} gap-1.5`}>
          {QUICK_PICKS.map((pick) => (
            <button
              key={pick.label}
              onClick={() => setPrompt(pick.prompt)}
              className={`text-xs px-2.5 py-1.5 rounded-lg border transition-colors text-left w-full
                ${prompt === pick.prompt
                  ? "border-[#f27038]/50 bg-[#f27038]/10 text-[#f27038]"
                  : "border-gray-200 bg-gray-50 hover:bg-[#f27038]/10 hover:border-[#f27038]/30 hover:text-[#f27038]"
                }`}
            >
              {pick.label}
            </button>
          ))}
        </div>
      </div>

      {/* Custom prompt */}
      <div className={expanded ? "flex-1 flex flex-col" : ""}>
        <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
          Or describe your report
        </div>
        <textarea
          ref={textareaRef}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="e.g. Focus on remarketing performance and flag any ads with CPL above $60"
          className={`text-sm border border-gray-200 rounded-lg p-2.5 w-full resize-none
            focus:ring-2 focus:ring-[#f27038]/50 focus:border-[#f27038]/50 outline-none
            overflow-hidden leading-relaxed
            ${expanded ? "min-h-[180px] flex-1" : "min-h-[80px]"}`}
          style={expanded ? {} : { maxHeight: "240px", overflowY: "auto" }}
        />
        {expanded && (
          <p className="text-xs text-gray-400 mt-1">
            Be as specific as you'd like — JARVIS will tailor the report to your request.
          </p>
        )}
      </div>

      {/* Send to channel */}
      <div>
        <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
          Send to
        </div>
        <select
          value={selectedChannel}
          onChange={(e) => {
            if (e.target.value === "__add__") {
              setShowAddChannel(true);
            } else {
              setSelectedChannel(e.target.value);
              setShowAddChannel(false);
            }
          }}
          className="text-sm border border-gray-200 rounded-lg p-2 w-full focus:ring-2 focus:ring-[#f27038]/50 focus:border-[#f27038]/50 outline-none bg-white"
        >
          {channels.map((ch) => (
            <option key={ch} value={ch}>
              #{ch}
            </option>
          ))}
          <option value="__add__">＋ Add a Slack channel…</option>
        </select>

        {/* Add-to-channel panel */}
        {showAddChannel && (
          <div className="mt-2 rounded-lg border border-[#f27038]/20 bg-[#f27038]/5 p-3 space-y-2.5">
            {/* Instructions */}
            <div className="flex gap-2">
              <Info className="h-3.5 w-3.5 text-[#f27038] shrink-0 mt-0.5" />
              <div className="text-xs text-gray-700 space-y-1">
                <p className="font-semibold">Invite JARVIS to a channel first:</p>
                <ol className="list-decimal list-inside space-y-0.5 text-gray-600">
                  <li>Open the Slack channel you want to add</li>
                  <li>Type <code className="bg-[#f27038]/10 px-1 rounded font-mono">/invite @Jarvis</code> and send</li>
                  <li>Then enter the channel name below</li>
                </ol>
              </div>
            </div>

            {/* Channel name input */}
            <div className="flex gap-1.5">
              <div className="flex items-center gap-1 flex-1 border border-[#f27038]/30 rounded-lg bg-white px-2 focus-within:ring-2 focus-within:ring-[#f27038]/50">
                <Hash className="h-3 w-3 text-[#f27038] shrink-0" />
                <input
                  type="text"
                  value={newChannelName}
                  onChange={(e) => setNewChannelName(e.target.value.replace(/^#/, "").replace(/\s/g, "-").toLowerCase())}
                  onKeyDown={(e) => { if (e.key === "Enter") handleAddChannel(); }}
                  placeholder="channel-name"
                  className="text-sm py-1.5 flex-1 outline-none bg-transparent placeholder-gray-400"
                  autoFocus
                />
              </div>
              <button
                onClick={handleAddChannel}
                disabled={!newChannelName.trim() || addingChannel}
                className="text-xs bg-[#f27038] hover:bg-[#d4612e] text-white px-3 py-1.5 rounded-lg font-medium transition-colors disabled:opacity-50 flex items-center gap-1"
              >
                {addingChannel ? <Loader2 className="h-3 w-3 animate-spin" /> : <Plus className="h-3 w-3" />}
                Add
              </button>
              <button
                onClick={() => { setShowAddChannel(false); setNewChannelName(""); setAddChannelError(""); }}
                className="text-xs text-gray-400 hover:text-gray-600 px-2 py-1.5 rounded-lg transition-colors"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
            {addChannelError && (
              <p className="text-xs text-red-600">{addChannelError}</p>
            )}
          </div>
        )}
      </div>

      {/* Auto-schedule */}
      <div>
        <div className="flex items-center gap-1.5 mb-2">
          <Clock className="h-3.5 w-3.5 text-gray-400" />
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
            Auto-schedule
          </span>
        </div>
        {/* Row 1: day + time */}
        <div className="flex gap-2 mb-2">
          <select
            value={scheduleDay}
            onChange={(e) => handleDayChange(e.target.value)}
            className="text-sm border border-gray-200 rounded-lg p-2 flex-1 focus:ring-2 focus:ring-[#f27038]/50 focus:border-[#f27038]/50 outline-none bg-white"
          >
            {DAYS.map((d) => (
              <option key={d} value={d}>
                {DAY_LABELS[d]}
              </option>
            ))}
          </select>
          <select
            value={scheduleHour}
            onChange={(e) => handleHourChange(Number(e.target.value))}
            className="text-sm border border-gray-200 rounded-lg p-2 flex-1 focus:ring-2 focus:ring-[#f27038]/50 focus:border-[#f27038]/50 outline-none bg-white"
          >
            {Array.from({ length: 24 }, (_, i) => (
              <option key={i} value={i}>
                {formatHour(i)}
              </option>
            ))}
          </select>
        </div>
        {/* Row 2: timezone */}
        <select
          value={scheduleTimezone}
          onChange={(e) => handleTimezoneChange(e.target.value)}
          className="text-sm border border-gray-200 rounded-lg p-2 w-full focus:ring-2 focus:ring-[#f27038]/50 focus:border-[#f27038]/50 outline-none bg-white mb-2"
        >
          {TIMEZONES.map((tz) => (
            <option key={tz.value} value={tz.value}>
              {tz.label}
            </option>
          ))}
        </select>
        {/* Set Schedule button */}
        <button
          onClick={handleScheduleSave}
          disabled={scheduleSaveState === "saving"}
          className={`w-full text-sm rounded-lg px-4 py-2 font-medium flex items-center justify-center gap-2 transition-colors border
            ${scheduleSaveState === "saved"
              ? "border-green-300 bg-green-50 text-green-700"
              : scheduleSaveState === "error"
              ? "border-red-300 bg-red-50 text-red-700"
              : "border-[#f27038]/50 text-[#f27038] hover:bg-[#f27038]/5 disabled:opacity-50"
            }`}
        >
          {scheduleSaveState === "saving" ? (
            <><Loader2 className="h-3.5 w-3.5 animate-spin" />Saving…</>
          ) : scheduleSaveState === "saved" ? (
            <><CheckCircle className="h-3.5 w-3.5" />Schedule saved!</>
          ) : scheduleSaveState === "error" ? (
            <>Failed to save — try again</>
          ) : (
            <><Calendar className="h-3.5 w-3.5" />Set Schedule</>
          )}
        </button>
      </div>

      {/* Send button */}
      <div className={expanded ? "pt-1" : ""}>
        <button
          onClick={handleSend}
          disabled={isSending || !prompt.trim()}
          className="bg-[#f27038] hover:bg-[#d4612e] text-white rounded-lg px-4 py-2.5 w-full font-medium text-sm flex items-center justify-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSending ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Sending…
            </>
          ) : sendState === "success" ? (
            <>
              <CheckCircle className="h-4 w-4 text-green-300" />
              <span className="text-green-100">{sendMessage}</span>
            </>
          ) : sendState === "error" ? (
            <span className="text-red-200 text-xs">{sendMessage}</span>
          ) : (
            <>
              <Send className="h-4 w-4" />
              Send Report
            </>
          )}
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function JarvisSidebar({ startDate, endDate }: JarvisSidebarProps) {
  const [prompt, setPrompt] = useState("");
  const [channels, setChannels] = useState<string[]>(["jarvis-schumacher"]);
  const [selectedChannel, setSelectedChannel] = useState("jarvis-schumacher");
  const [scheduleDay, setScheduleDay] = useState("monday");
  const [scheduleHour, setScheduleHour] = useState(9);
  const [scheduleTimezone, setScheduleTimezone] = useState<string>(detectTimezone);
  const [isSending, setIsSending] = useState(false);
  const [sendState, setSendState] = useState<"idle" | "success" | "error">("idle");
  const [sendMessage, setSendMessage] = useState("");
  const [scheduleSaveState, setScheduleSaveState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [isExpanded, setIsExpanded] = useState(false);

  // Load channels + schedule on mount
  useEffect(() => {
    api.getSlackChannels().then((res) => {
      if (res.channels?.length) setChannels(res.channels);
    }).catch(() => {});

    api.getJarvisSchedule().then((s) => {
      setSelectedChannel(s.channel);
      setScheduleDay(s.day);
      setScheduleHour(s.hour);
      if (s.timezone) setScheduleTimezone(s.timezone);
    }).catch(() => {});
  }, []);

  // Close modal on Escape
  useEffect(() => {
    if (!isExpanded) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") setIsExpanded(false);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [isExpanded]);

  // Lock body scroll when modal is open
  useEffect(() => {
    document.body.style.overflow = isExpanded ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [isExpanded]);

  const handleDayChange = (day: string) => {
    setScheduleDay(day);
  };

  const handleHourChange = (hour: number) => {
    setScheduleHour(hour);
  };

  const handleTimezoneChange = (timezone: string) => {
    setScheduleTimezone(timezone);
  };

  const handleScheduleSave = async () => {
    setScheduleSaveState("saving");
    try {
      await api.updateJarvisSchedule({
        channel: selectedChannel,
        day: scheduleDay,
        hour: scheduleHour,
        timezone: scheduleTimezone,
      });
      setScheduleSaveState("saved");
      setTimeout(() => setScheduleSaveState("idle"), 2500);
    } catch {
      setScheduleSaveState("error");
      setTimeout(() => setScheduleSaveState("idle"), 3000);
    }
  };

  const handleSend = async () => {
    if (!prompt.trim()) return;
    setIsSending(true);
    setSendState("idle");
    try {
      const result = await api.sendJarvisReport({
        prompt: prompt.trim(),
        channel: selectedChannel,
        startDate,
        endDate,
      });
      if (result.success) {
        setSendState("success");
        setSendMessage(`Sent to #${result.channel || selectedChannel}!`);
      } else {
        setSendState("error");
        setSendMessage(result.error || "Failed to send report");
      }
    } catch {
      setSendState("error");
      setSendMessage("Failed to send report");
    } finally {
      setIsSending(false);
      setTimeout(() => setSendState("idle"), 3000);
    }
  };

  const sharedFormProps = {
    prompt,
    setPrompt,
    channels,
    setChannels,
    selectedChannel,
    setSelectedChannel,
    scheduleDay,
    scheduleHour,
    scheduleTimezone,
    scheduleSaveState,
    isSending,
    sendState,
    sendMessage,
    handleDayChange,
    handleHourChange,
    handleTimezoneChange,
    handleScheduleSave,
    handleSend,
  };

  return (
    <>
      {/* ── Sidebar panel ───────────────────────────────────────────────── */}
      <div className="bg-white border border-gray-200 rounded-xl shadow-sm w-80 shrink-0 flex flex-col">
        {/* Header */}
        <div className="bg-gradient-to-br from-[#1e1e1e] to-[#2a2a2a] rounded-t-xl px-4 py-3">
          <div className="flex items-center gap-2">
            <span className="text-xl">🤖</span>
            <div className="flex-1 min-w-0">
              <div className="text-white font-bold text-sm">Ask JARVIS</div>
              <div className="text-gray-400 text-xs">Send a custom report to Slack</div>
            </div>
            <button
              onClick={() => setIsExpanded(true)}
              title="Expand to full view"
              className="ml-auto text-gray-400 hover:text-white transition-colors p-1 rounded hover:bg-white/10"
            >
              <Maximize2 className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="px-4 py-3 flex-1 overflow-y-auto">
          <JarvisForm {...sharedFormProps} expanded={false} />
        </div>
      </div>

      {/* ── Full-screen modal ────────────────────────────────────────────── */}
      {isExpanded && typeof window !== "undefined" && createPortal(
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-6"
          onClick={(e) => { if (e.target === e.currentTarget) setIsExpanded(false); }}
        >
          {/* Backdrop */}
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" />

          {/* Modal panel */}
          <div className="relative z-10 bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden">
            {/* Modal header */}
            <div className="bg-gradient-to-br from-[#1e1e1e] to-[#2a2a2a] px-6 py-4 flex items-center gap-3 shrink-0">
              <span className="text-2xl">🤖</span>
              <div className="flex-1 min-w-0">
                <div className="text-white font-bold text-base">Ask JARVIS</div>
                <div className="text-gray-400 text-sm">
                  Customize and send a report to Slack · {startDate} – {endDate}
                </div>
              </div>
              <button
                onClick={() => setIsExpanded(false)}
                title="Collapse to sidebar"
                className="text-gray-400 hover:text-white transition-colors p-1.5 rounded-lg hover:bg-white/10 flex items-center gap-1.5"
              >
                <Minimize2 className="h-4 w-4" />
                <span className="text-xs">Collapse</span>
              </button>
              <button
                onClick={() => setIsExpanded(false)}
                title="Close"
                className="text-gray-400 hover:text-white transition-colors p-1.5 rounded-lg hover:bg-white/10"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Modal body */}
            <div className="flex-1 overflow-y-auto px-6 py-5">
              <JarvisForm {...sharedFormProps} expanded={true} />
            </div>
          </div>
        </div>,
        document.body
      )}
    </>
  );
}
