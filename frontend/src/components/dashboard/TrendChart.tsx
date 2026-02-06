"use client";

import { useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DailyMetric, formatCurrency, formatNumber } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

interface TrendChartProps {
  data: DailyMetric[];
  title?: string;
}

type MetricKey = "spend" | "leads" | "clicks" | "conversions" | "costPerLead";

interface MetricConfig {
  key: MetricKey;
  label: string;
  color: string;
  yAxisId: "left" | "right";
  strokeWidth: number;
}

const METRICS: MetricConfig[] = [
  { key: "spend", label: "Spend", color: "#1f2937", yAxisId: "left", strokeWidth: 2 },
  { key: "leads", label: "Leads", color: "#22c55e", yAxisId: "right", strokeWidth: 3 },
  { key: "costPerLead", label: "CPL", color: "#f59e0b", yAxisId: "left", strokeWidth: 2 },
  { key: "clicks", label: "Clicks", color: "#6366f1", yAxisId: "right", strokeWidth: 2 },
  { key: "conversions", label: "Conversions", color: "#ec4899", yAxisId: "right", strokeWidth: 2 },
];

export function TrendChart({ data, title = "Performance Trends" }: TrendChartProps) {
  const [visibleMetrics, setVisibleMetrics] = useState<Set<MetricKey>>(
    new Set(["spend", "leads"])
  );

  const toggleMetric = (metric: MetricKey) => {
    setVisibleMetrics((prev) => {
      const next = new Set(prev);
      if (next.has(metric)) {
        next.delete(metric);
      } else {
        next.add(metric);
      }
      return next;
    });
  };

  const selectAll = () => {
    setVisibleMetrics(new Set(["spend", "leads", "costPerLead", "clicks", "conversions"]));
  };

  const clearAll = () => {
    setVisibleMetrics(new Set());
  };

  // Format date for display — append T00:00:00 to avoid timezone shift
  const formattedData = data.map((item) => ({
    ...item,
    displayDate: new Date(item.date + "T00:00:00").toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    }),
  }));

  // Check if we need the left Y-axis (spend/CPL) or right Y-axis (count metrics)
  const showLeftAxis = visibleMetrics.has("spend") || visibleMetrics.has("costPerLead");
  const showRightAxis = visibleMetrics.has("leads") || visibleMetrics.has("clicks") || visibleMetrics.has("conversions");

  // Show dots when few data points for better readability
  const showDots = data.length <= 14;

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <CardTitle className="text-lg">{title}</CardTitle>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-muted-foreground mr-1">Metrics:</span>
            {METRICS.map((metric) => {
              const isActive = visibleMetrics.has(metric.key);
              return (
                <button
                  key={metric.key}
                  onClick={() => toggleMetric(metric.key)}
                  className={cn(
                    "px-3 py-1.5 text-xs font-medium rounded-full border transition-all",
                    isActive
                      ? "border-transparent text-white shadow-sm"
                      : "border-gray-300 text-gray-600 hover:bg-gray-100"
                  )}
                  style={{
                    backgroundColor: isActive ? metric.color : "white",
                  }}
                >
                  {metric.label}
                </button>
              );
            })}
            <div className="flex gap-1 ml-2 border-l pl-2">
              <button
                onClick={selectAll}
                className="px-2 py-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
              >
                All
              </button>
              <button
                onClick={clearAll}
                className="px-2 py-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
              >
                Clear
              </button>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-[350px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={formattedData}
              margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis
                dataKey="displayDate"
                tick={{ fontSize: 12 }}
                tickLine={false}
                axisLine={false}
                className="text-muted-foreground"
              />
              {showLeftAxis && (
                <YAxis
                  yAxisId="left"
                  tick={{ fontSize: 12 }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(value) => `$${formatNumber(value)}`}
                  className="text-muted-foreground"
                />
              )}
              {showRightAxis && (
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  tick={{ fontSize: 12 }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(value) => formatNumber(value)}
                  className="text-muted-foreground"
                />
              )}
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "8px",
                }}
                formatter={(value, name) => {
                  const numValue = typeof value === "number" ? value : 0;
                  if (name === "Spend") return [formatCurrency(numValue), "Spend"];
                  if (name === "CPL") return [formatCurrency(numValue), "CPL"];
                  if (name === "Clicks") return [formatNumber(numValue), "Clicks"];
                  if (name === "Leads") return [numValue, "Leads"];
                  if (name === "Conversions") return [numValue, "Conversions"];
                  return [numValue, name];
                }}
                labelFormatter={(label) => `Date: ${label}`}
              />
              {METRICS.map((metric) => {
                const isVisible = visibleMetrics.has(metric.key);
                return (
                  <Line
                    key={metric.key}
                    yAxisId={metric.yAxisId}
                    type="monotone"
                    dataKey={metric.key}
                    name={metric.label}
                    stroke={isVisible ? metric.color : "transparent"}
                    strokeWidth={isVisible ? metric.strokeWidth : 0}
                    dot={isVisible && showDots ? { r: 3, fill: metric.color, stroke: metric.color } : false}
                    activeDot={isVisible ? { r: metric.key === "leads" ? 6 : 5 } : false}
                    hide={!isVisible}
                    legendType="none"
                  />
                );
              })}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
