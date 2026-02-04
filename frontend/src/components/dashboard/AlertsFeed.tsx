"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  AlertTriangle,
  XCircle,
  TrendingUp,
  DollarSign,
  Link2Off,
  CheckCircle,
} from "lucide-react";
import { AuditAlert } from "@/lib/mock-data";
import { cn } from "@/lib/utils";
import { formatDistanceToNow } from "date-fns";

interface AlertsFeedProps {
  alerts: AuditAlert[];
  title?: string;
  onAcknowledge?: (alertId: string) => void;
}

export function AlertsFeed({
  alerts,
  title = "Audit Alerts",
  onAcknowledge,
}: AlertsFeedProps) {
  const getAlertIcon = (type: AuditAlert["type"]) => {
    switch (type) {
      case "URL_ERROR":
        return <Link2Off className="h-4 w-4" />;
      case "CONTENT_MISMATCH":
        return <AlertTriangle className="h-4 w-4" />;
      case "HIGH_SPEND_LOW_CONV":
        return <DollarSign className="h-4 w-4" />;
      case "SPEND_ANOMALY":
        return <TrendingUp className="h-4 w-4" />;
      case "HIGH_CPC":
        return <DollarSign className="h-4 w-4" />;
      default:
        return <AlertTriangle className="h-4 w-4" />;
    }
  };

  const getSeverityBadge = (severity: AuditAlert["severity"]) => {
    switch (severity) {
      case "high":
        return (
          <Badge variant="destructive" className="text-xs">
            High
          </Badge>
        );
      case "medium":
        return (
          <Badge className="bg-yellow-100 text-yellow-800 hover:bg-yellow-100 text-xs">
            Medium
          </Badge>
        );
      case "low":
        return (
          <Badge variant="secondary" className="text-xs">
            Low
          </Badge>
        );
      default:
        return <Badge variant="outline">{severity}</Badge>;
    }
  };

  const getAlertTypeLabel = (type: AuditAlert["type"]) => {
    switch (type) {
      case "URL_ERROR":
        return "URL Error";
      case "CONTENT_MISMATCH":
        return "Content Mismatch";
      case "HIGH_SPEND_LOW_CONV":
        return "High Spend / Low Conv";
      case "SPEND_ANOMALY":
        return "Spend Anomaly";
      case "HIGH_CPC":
        return "High CPC";
      default:
        return type;
    }
  };

  const unacknowledgedCount = alerts.filter((a) => !a.acknowledged).length;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">{title}</CardTitle>
          {unacknowledgedCount > 0 && (
            <Badge variant="destructive">{unacknowledgedCount} new</Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3 max-h-[400px] overflow-y-auto">
          {alerts.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <CheckCircle className="h-12 w-12 text-green-500 mb-2" />
              <p className="text-sm text-muted-foreground">
                No audit alerts at this time
              </p>
            </div>
          ) : (
            alerts.map((alert, index) => (
              <div key={alert.id}>
                <div
                  className={cn(
                    "flex flex-col gap-2 p-3 rounded-lg",
                    alert.acknowledged
                      ? "bg-muted/30 opacity-60"
                      : "bg-muted/50"
                  )}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <div
                        className={cn(
                          "p-1.5 rounded",
                          alert.severity === "high" && "bg-red-100 text-red-700",
                          alert.severity === "medium" &&
                            "bg-yellow-100 text-yellow-700",
                          alert.severity === "low" && "bg-gray-100 text-gray-700"
                        )}
                      >
                        {getAlertIcon(alert.type)}
                      </div>
                      <div className="flex flex-col">
                        <span className="text-sm font-medium">
                          {getAlertTypeLabel(alert.type)}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {alert.adName}
                        </span>
                      </div>
                    </div>
                    {getSeverityBadge(alert.severity)}
                  </div>
                  <p className="text-sm text-foreground">{alert.message}</p>
                  <p className="text-xs text-muted-foreground">
                    <span className="font-medium">Recommendation:</span>{" "}
                    {alert.recommendation}
                  </p>
                  <div className="flex items-center justify-between mt-1">
                    <span className="text-xs text-muted-foreground">
                      {formatDistanceToNow(new Date(alert.createdAt), {
                        addSuffix: true,
                      })}
                    </span>
                    {!alert.acknowledged && onAcknowledge && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 text-xs"
                        onClick={() => onAcknowledge(alert.id)}
                      >
                        Acknowledge
                      </Button>
                    )}
                  </div>
                </div>
                {index < alerts.length - 1 && <Separator className="my-2" />}
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}
