"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  LineChart,
  Line,
  ResponsiveContainer,
} from "recharts";

interface MetricCardProps {
  title: string;
  value: string;
  subtitle?: string;
  change?: number;
  changeLabel?: string; // defaults to "vs last month"
  invertTrend?: boolean; // true for cost metrics where down = good (CPL, CPC, CPM, CPA)
  icon?: React.ReactNode;
  className?: string;
  sparklineData?: number[];
  sparklineColor?: string;
}

export function MetricCard({
  title,
  value,
  subtitle,
  change,
  changeLabel = "vs prior month",
  invertTrend = false,
  icon,
  className,
  sparklineData,
  sparklineColor = "#22c55e",
}: MetricCardProps) {
  const isUp = change !== undefined && change > 0;
  const isDown = change !== undefined && change < 0;
  const isNeutral = change === undefined || change === 0;

  // For cost metrics (invertTrend), down is good (green) and up is bad (red)
  const isGood = invertTrend ? isDown : isUp;
  const isBad = invertTrend ? isUp : isDown;

  // Convert sparkline data to chart format
  const chartData = sparklineData?.map((value, index) => ({ value, index }));

  return (
    <Card className={cn("", className)}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        {icon && <div className="text-muted-foreground">{icon}</div>}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {subtitle && (
          <div className="text-xs text-muted-foreground mt-1">{subtitle}</div>
        )}
        {change !== undefined && (
          <div className="flex items-center gap-1 mt-1">
            {isUp && (
              <TrendingUp className={cn("h-3 w-3", isGood ? "text-green-600" : "text-red-600")} />
            )}
            {isDown && (
              <TrendingDown className={cn("h-3 w-3", isBad ? "text-red-600" : "text-green-600")} />
            )}
            {isNeutral && (
              <Minus className="h-3 w-3 text-muted-foreground" />
            )}
            <span
              className={cn(
                "text-xs",
                isGood && "text-green-600",
                isBad && "text-red-600",
                isNeutral && "text-muted-foreground"
              )}
            >
              {isUp ? "+" : ""}
              {change.toFixed(1)}% {changeLabel}
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
