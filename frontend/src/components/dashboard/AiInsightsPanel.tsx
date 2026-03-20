"use client";

import { useState, useEffect, useCallback } from "react";
import { RefreshCw } from "lucide-react";
import { api } from "@/lib/api";

interface AiInsightsPanelProps {
  startDate: string;
  endDate: string;
  compareStart?: string;
  compareEnd?: string;
}

interface Insights {
  headline: string;
  bullets: string[];
  flags: string[];
}

export function AiInsightsPanel({
  startDate,
  endDate,
  compareStart,
  compareEnd,
}: AiInsightsPanelProps) {
  const [insights, setInsights] = useState<Insights | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [period, setPeriod] = useState<string>("");

  const fetchInsights = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await api.getAiInsights({
        startDate,
        endDate,
        compareStart,
        compareEnd,
      });
      if (result.success && result.insights) {
        setInsights(result.insights);
        setPeriod(result.period || "");
      } else {
        setError(result.error || "Could not generate insights");
      }
    } catch {
      setError("Could not generate insights");
    } finally {
      setIsLoading(false);
    }
  }, [startDate, endDate, compareStart, compareEnd]);

  useEffect(() => {
    fetchInsights();
  }, [fetchInsights]);

  return (
    <div className="bg-gradient-to-r from-[#f27038]/5 to-[#f27038]/10 border border-[#f27038]/20 rounded-xl p-4">
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <span className="text-lg">🧠</span>
        <span className="text-[#f27038] font-semibold text-sm">AI Insights</span>
        {period && !isLoading && (
          <span className="text-xs text-gray-500 ml-1">{period}</span>
        )}
        <button
          onClick={fetchInsights}
          disabled={isLoading}
          className="ml-auto p-1 rounded hover:bg-[#f27038]/10 transition-colors disabled:opacity-50"
          title="Refresh insights"
        >
          <RefreshCw className={`h-3.5 w-3.5 text-[#f27038] ${isLoading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="space-y-2 animate-pulse">
          <div className="h-3.5 bg-[#f27038]/10 rounded w-3/4" />
          <div className="h-3 bg-[#f27038]/10 rounded w-full" />
          <div className="h-3 bg-[#f27038]/10 rounded w-5/6" />
        </div>
      )}

      {/* Error state */}
      {!isLoading && error && (
        <p className="text-xs text-gray-400 italic">{error}</p>
      )}

      {/* Loaded state */}
      {!isLoading && !error && insights && (
        <div>
          {/* Headline */}
          <p className="text-gray-900 font-semibold text-sm mb-2">{insights.headline}</p>

          {/* Bullets */}
          {insights.bullets.length > 0 && (
            <ul className="space-y-1 mb-3">
              {insights.bullets.map((bullet, i) => (
                <li key={i} className="flex gap-2 text-sm text-gray-700">
                  <span className="text-[#f27038] shrink-0 font-bold">•</span>
                  <span>{bullet}</span>
                </li>
              ))}
            </ul>
          )}

          {/* Flags */}
          {insights.flags && insights.flags.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {insights.flags.map((flag, i) => (
                <span
                  key={i}
                  className="bg-orange-50 border border-orange-200 text-orange-700 text-xs px-2 py-1 rounded-full"
                >
                  {flag}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
