"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Send, Clock, Loader2, CheckCircle } from "lucide-react";
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

function formatHour(h: number): string {
  if (h === 0) return "12:00 AM";
  if (h < 12) return `${h}:00 AM`;
  if (h === 12) return "12:00 PM";
  return `${h - 12}:00 PM`;
}

export function JarvisSidebar({ startDate, endDate }: JarvisSidebarProps) {
  const [prompt, setPrompt] = useState("");
  const [channels, setChannels] = useState<string[]>(["jarvis-schumacher"]);
  const [selectedChannel, setSelectedChannel] = useState("jarvis-schumacher");
  const [scheduleDay, setScheduleDay] = useState("monday");
  const [scheduleHour, setScheduleHour] = useState(9);
  const [isSending, setIsSending] = useState(false);
  const [sendState, setSendState] = useState<"idle" | "success" | "error">("idle");
  const [sendMessage, setSendMessage] = useState("");
  const [scheduleSaved, setScheduleSaved] = useState(false);

  const scheduleDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Load channels and schedule on mount
  useEffect(() => {
    api.getSlackChannels().then((res) => {
      if (res.channels && res.channels.length > 0) {
        setChannels(res.channels);
      }
    }).catch(() => {});

    api.getJarvisSchedule().then((schedule) => {
      setSelectedChannel(schedule.channel);
      setScheduleDay(schedule.day);
      setScheduleHour(schedule.hour);
    }).catch(() => {});
  }, []);

  const handleScheduleChange = useCallback(
    (channel: string, day: string, hour: number) => {
      if (scheduleDebounceRef.current) clearTimeout(scheduleDebounceRef.current);
      scheduleDebounceRef.current = setTimeout(async () => {
        try {
          await api.updateJarvisSchedule({ channel, day, hour });
          setScheduleSaved(true);
          setTimeout(() => setScheduleSaved(false), 2000);
        } catch {}
      }, 500);
    },
    []
  );

  const handleDayChange = (day: string) => {
    setScheduleDay(day);
    handleScheduleChange(selectedChannel, day, scheduleHour);
  };

  const handleHourChange = (hour: number) => {
    setScheduleHour(hour);
    handleScheduleChange(selectedChannel, scheduleDay, hour);
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

  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-sm w-80 shrink-0 flex flex-col">
      {/* Header */}
      <div className="bg-gradient-to-br from-indigo-600 to-purple-700 rounded-t-xl px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="text-xl">🤖</span>
          <div>
            <div className="text-white font-bold text-sm">Ask JARVIS</div>
            <div className="text-indigo-200 text-xs">Send a custom report to Slack</div>
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="px-4 py-3 space-y-4 flex-1 overflow-y-auto">
        {/* Quick picks */}
        <div>
          <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
            Quick report
          </div>
          <div className="grid grid-cols-2 gap-1.5">
            {QUICK_PICKS.map((pick) => (
              <button
                key={pick.label}
                onClick={() => setPrompt(pick.prompt)}
                className="text-xs px-2.5 py-1.5 rounded-lg border border-gray-200 bg-gray-50 hover:bg-indigo-50 hover:border-indigo-200 hover:text-indigo-700 transition-colors text-left w-full"
              >
                {pick.label}
              </button>
            ))}
          </div>
        </div>

        {/* Custom prompt */}
        <div>
          <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
            Or describe your report
          </div>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g. Focus on remarketing performance and flag any ads with CPL above $60"
            className="text-sm border border-gray-200 rounded-lg p-2.5 w-full resize-none h-20 focus:ring-2 focus:ring-indigo-300 focus:border-indigo-300 outline-none"
          />
        </div>

        {/* Send to channel */}
        <div>
          <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
            Send to
          </div>
          <select
            value={selectedChannel}
            onChange={(e) => setSelectedChannel(e.target.value)}
            className="text-sm border border-gray-200 rounded-lg p-2 w-full focus:ring-2 focus:ring-indigo-300 focus:border-indigo-300 outline-none bg-white"
          >
            {channels.map((ch) => (
              <option key={ch} value={ch}>
                #{ch}
              </option>
            ))}
          </select>
        </div>

        {/* Auto-schedule */}
        <div>
          <div className="flex items-center gap-1.5 mb-2">
            <Clock className="h-3.5 w-3.5 text-gray-400" />
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
              Auto-schedule
            </span>
            {scheduleSaved && (
              <span className="ml-auto text-xs text-green-600 font-medium animate-pulse">
                ✓ Saved
              </span>
            )}
          </div>
          <div className="flex gap-2">
            <select
              value={scheduleDay}
              onChange={(e) => handleDayChange(e.target.value)}
              className="text-sm border border-gray-200 rounded-lg p-2 flex-1 focus:ring-2 focus:ring-indigo-300 focus:border-indigo-300 outline-none bg-white"
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
              className="text-sm border border-gray-200 rounded-lg p-2 flex-1 focus:ring-2 focus:ring-indigo-300 focus:border-indigo-300 outline-none bg-white"
            >
              {Array.from({ length: 24 }, (_, i) => (
                <option key={i} value={i}>
                  {formatHour(i)}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Footer — Send button */}
      <div className="px-4 pb-4 pt-2 border-t border-gray-100">
        <button
          onClick={handleSend}
          disabled={isSending || !prompt.trim()}
          className="bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg px-4 py-2.5 w-full font-medium text-sm flex items-center justify-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSending ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Sending...
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
