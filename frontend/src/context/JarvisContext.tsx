"use client";

import React, { createContext, useContext, useState, useCallback, useEffect } from "react";
import { api } from "@/lib/api";

export type Section = "kpi_cards" | "active_ads" | "trend_chart" | "campaign_table" | "alerts";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
}

interface JarvisContextValue {
  isOpen: boolean;
  activeSection: Section | null;
  threads: Record<string, ChatMessage[]>;
  isTyping: boolean;
  sectionData: Record<string, unknown>;
  setSectionData: (section: Section, data: unknown) => void;
  openForSection: (section: Section) => void;
  close: () => void;
  sendMessage: (content: string) => Promise<void>;
  clearThread: (section: Section) => void;
  isExpanded: boolean;
  setIsExpanded: (v: boolean) => void;
  channels: string[];
  setChannels: (chs: string[]) => void;
  selectedChannel: string;
  setSelectedChannel: (ch: string) => void;
  scheduleDay: string;
  scheduleHour: number;
  scheduleTimezone: string;
  scheduleSaveState: "idle" | "saving" | "saved" | "error";
  handleDayChange: (d: string) => void;
  handleHourChange: (h: number) => void;
  handleTimezoneChange: (tz: string) => void;
  handleScheduleSave: () => void;
  slackSendState: "idle" | "sending" | "sent" | "error";
  handleSendToSlack: () => void;
  startDate: string;
  endDate: string;
  setDateRange: (startDate: string, endDate: string) => void;
}

const JarvisContext = createContext<JarvisContextValue | null>(null);

export function useJarvis() {
  const ctx = useContext(JarvisContext);
  if (!ctx) throw new Error("useJarvis must be used within JarvisProvider");
  return ctx;
}

function detectTimezone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "America/New_York";
  } catch {
    return "America/New_York";
  }
}

function generateId(): string {
  return Math.random().toString(36).slice(2, 10);
}

export function JarvisProvider({ children }: { children: React.ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);
  const [activeSection, setActiveSection] = useState<Section | null>(null);
  const [threads, setThreads] = useState<Record<string, ChatMessage[]>>({});
  const [isTyping, setIsTyping] = useState(false);
  const [sectionData, setSectionDataState] = useState<Record<string, unknown>>({});
  const [isExpanded, setIsExpanded] = useState(false);

  const [startDate, setStartDate] = useState<string>(() => {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10);
  });
  const [endDate, setEndDate] = useState<string>(() => new Date().toISOString().slice(0, 10));

  const [channels, setChannels] = useState<string[]>(["jarvis-schumacher"]);
  const [selectedChannel, setSelectedChannel] = useState("jarvis-schumacher");
  const [scheduleDay, setScheduleDay] = useState("monday");
  const [scheduleHour, setScheduleHour] = useState(9);
  const [scheduleTimezone, setScheduleTimezone] = useState<string>(detectTimezone);
  const [scheduleSaveState, setScheduleSaveState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [slackSendState, setSlackSendState] = useState<"idle" | "sending" | "sent" | "error">("idle");

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

  const setSectionData = useCallback((section: Section, data: unknown) => {
    setSectionDataState(prev => ({ ...prev, [section]: data }));
  }, []);

  const openForSection = useCallback((section: Section) => {
    setActiveSection(section);
    setIsOpen(true);
  }, []);

  const close = useCallback(() => { setIsOpen(false); setIsExpanded(false); }, []);

  const clearThread = useCallback((section: Section) => {
    setThreads(prev => ({ ...prev, [section]: [] }));
  }, []);

  const sendMessage = useCallback(async (content: string) => {
    if (!activeSection) return;
    const userMsg: ChatMessage = { id: generateId(), role: "user", content, timestamp: Date.now() };
    setThreads(prev => ({ ...prev, [activeSection]: [...(prev[activeSection] || []), userMsg] }));
    setIsTyping(true);
    try {
      const currentThread = threads[activeSection] || [];
      const messages = [...currentThread, userMsg].map(m => ({ role: m.role, content: m.content }));
      const result = await api.jarvisChat({ section: activeSection, messages, startDate, endDate, sectionData: sectionData[activeSection] ?? null });
      const assistantMsg: ChatMessage = { id: generateId(), role: "assistant", content: result.reply || "Sorry, I couldn't generate a response.", timestamp: Date.now() };
      setThreads(prev => ({ ...prev, [activeSection]: [...(prev[activeSection] || []), assistantMsg] }));
    } catch {
      const errorMsg: ChatMessage = { id: generateId(), role: "assistant", content: "Sorry, I ran into an error. Please try again.", timestamp: Date.now() };
      setThreads(prev => ({ ...prev, [activeSection]: [...(prev[activeSection] || []), errorMsg] }));
    } finally {
      setIsTyping(false);
    }
  }, [activeSection, threads, startDate, endDate, sectionData]);

  const handleDayChange = (day: string) => setScheduleDay(day);
  const handleHourChange = (hour: number) => setScheduleHour(hour);
  const handleTimezoneChange = (tz: string) => setScheduleTimezone(tz);

  const handleScheduleSave = async () => {
    setScheduleSaveState("saving");
    try {
      await api.updateJarvisSchedule({ channel: selectedChannel, day: scheduleDay, hour: scheduleHour, timezone: scheduleTimezone });
      setScheduleSaveState("saved");
      setTimeout(() => setScheduleSaveState("idle"), 2500);
    } catch {
      setScheduleSaveState("error");
      setTimeout(() => setScheduleSaveState("idle"), 3000);
    }
  };

  const handleSendToSlack = async () => {
    if (!activeSection) return;
    const thread = threads[activeSection] || [];
    const lastAssistant = [...thread].reverse().find(m => m.role === "assistant");
    if (!lastAssistant) return;
    setSlackSendState("sending");
    try {
      // Pass the existing JARVIS response directly — avoids re-running Claude
      await api.sendJarvisReport({ message: lastAssistant.content, channel: selectedChannel, startDate, endDate });
      setSlackSendState("sent");
      setTimeout(() => setSlackSendState("idle"), 3000);
    } catch {
      setSlackSendState("error");
      setTimeout(() => setSlackSendState("idle"), 3000);
    }
  };

  const setDateRange = useCallback((s: string, e: string) => { setStartDate(s); setEndDate(e); }, []);

  return (
    <JarvisContext.Provider value={{
      isOpen, activeSection, threads, isTyping,
      sectionData, setSectionData,
      openForSection, close, sendMessage, clearThread,
      isExpanded, setIsExpanded,
      channels, setChannels, selectedChannel, setSelectedChannel,
      scheduleDay, scheduleHour, scheduleTimezone, scheduleSaveState,
      handleDayChange, handleHourChange, handleTimezoneChange, handleScheduleSave,
      slackSendState, handleSendToSlack,
      startDate, endDate, setDateRange,
    }}>
      {children}
    </JarvisContext.Provider>
  );
}
