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
  changeLabel?: string;
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
  changeLabel = "vs last period",
  icon,
  className,
  sparklineData,
  sparklineColor = "#22c55e",
}: MetricCardProps) {
  const isPositive = change !== undefined && change > 0;
  const isNegative = change !== undefined && change < 0;
  const isNeutral = change === undefined || change === 0;

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
            {isPositive && (
              <TrendingUp className="h-3 w-3 text-green-600" />
            )}
            {isNegative && (
              <TrendingDown className="h-3 w-3 text-red-600" />
            )}
            {isNeutral && (
              <Minus className="h-3 w-3 text-muted-foreground" />
            )}
            <span
              className={cn(
                "text-xs",
                isPositive && "text-green-600",
                isNegative && "text-red-600",
                isNeutral && "text-muted-foreground"
              )}
            >
              {isPositive ? "+" : ""}
              {change.toFixed(1)}% {changeLabel}
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
