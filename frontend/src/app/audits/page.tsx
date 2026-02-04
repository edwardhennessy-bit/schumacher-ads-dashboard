"use client";

import { useState, useEffect } from "react";
import { Header } from "@/components/layout/Header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  AlertTriangle,
  XCircle,
  Link2Off,
  DollarSign,
  TrendingUp,
  CheckCircle,
  Play,
  Filter,
} from "lucide-react";
import { api, AuditAlert } from "@/lib/api";
import { mockAuditAlerts } from "@/lib/mock-data";
import { formatDistanceToNow } from "date-fns";

function transformAlert(a: AuditAlert) {
  return {
    id: a.id,
    type: a.type,
    severity: a.severity,
    adId: a.ad_id,
    adName: a.ad_name,
    campaignName: a.campaign_name,
    message: a.message,
    recommendation: a.recommendation,
    createdAt: a.created_at,
    acknowledged: a.acknowledged,
  };
}

export default function AuditsPage() {
  const [alerts, setAlerts] = useState(mockAuditAlerts);
  const [isLoading, setIsLoading] = useState(false);
  const [filterSeverity, setFilterSeverity] = useState<string>("all");
  const [showAcknowledged, setShowAcknowledged] = useState(true);

  const fetchAlerts = async () => {
    setIsLoading(true);
    try {
      const data = await api.getAlerts();
      setAlerts(data.map(transformAlert));
    } catch (error) {
      console.log("API not available, using mock data");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
  }, []);

  const handleAcknowledge = async (alertId: string) => {
    try {
      await api.acknowledgeAlert(alertId);
      setAlerts((prev) =>
        prev.map((alert) =>
          alert.id === alertId ? { ...alert, acknowledged: true } : alert
        )
      );
    } catch (error) {
      // Still update locally even if API fails
      setAlerts((prev) =>
        prev.map((alert) =>
          alert.id === alertId ? { ...alert, acknowledged: true } : alert
        )
      );
    }
  };

  const handleRunAudit = async () => {
    setIsLoading(true);
    try {
      await api.runAudit();
      // Refetch alerts after audit
      await fetchAlerts();
    } catch (error) {
      console.log("Audit API not available");
    } finally {
      setIsLoading(false);
    }
  };

  const filteredAlerts = alerts.filter((a) => {
    if (filterSeverity !== "all" && a.severity !== filterSeverity) return false;
    if (!showAcknowledged && a.acknowledged) return false;
    return true;
  });

  const getAlertIcon = (type: string) => {
    switch (type) {
      case "URL_ERROR":
        return <Link2Off className="h-5 w-5" />;
      case "CONTENT_MISMATCH":
        return <AlertTriangle className="h-5 w-5" />;
      case "HIGH_SPEND_LOW_CONV":
        return <DollarSign className="h-5 w-5" />;
      case "SPEND_ANOMALY":
        return <TrendingUp className="h-5 w-5" />;
      case "HIGH_CPC":
        return <DollarSign className="h-5 w-5" />;
      default:
        return <AlertTriangle className="h-5 w-5" />;
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "high":
        return "bg-red-100 text-red-700";
      case "medium":
        return "bg-yellow-100 text-yellow-700";
      case "low":
        return "bg-gray-100 text-gray-700";
      default:
        return "bg-gray-100 text-gray-700";
    }
  };

  const getTypeLabel = (type: string) => {
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

  const summaryStats = {
    total: alerts.length,
    unacknowledged: alerts.filter((a) => !a.acknowledged).length,
    high: alerts.filter((a) => a.severity === "high").length,
    medium: alerts.filter((a) => a.severity === "medium").length,
    low: alerts.filter((a) => a.severity === "low").length,
  };

  return (
    <div className="min-h-screen bg-background">
      <Header
        title="Audits"
        subtitle="Smart Audit Results & Alerts"
        onRefresh={fetchAlerts}
        isLoading={isLoading}
      />

      <div className="p-6 space-y-6">
        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total Alerts
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{summaryStats.total}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Unacknowledged
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">
                {summaryStats.unacknowledged}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                High Severity
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">{summaryStats.high}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Medium Severity
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-yellow-600">
                {summaryStats.medium}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Low Severity
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-gray-600">{summaryStats.low}</div>
            </CardContent>
          </Card>
        </div>

        {/* Actions & Filters */}
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex gap-2">
            <Button onClick={handleRunAudit} disabled={isLoading}>
              <Play className="h-4 w-4 mr-2" />
              Run Audit
            </Button>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex gap-2">
              {["all", "high", "medium", "low"].map((severity) => (
                <Button
                  key={severity}
                  variant={filterSeverity === severity ? "default" : "outline"}
                  size="sm"
                  onClick={() => setFilterSeverity(severity)}
                >
                  {severity === "all" ? "All" : severity.charAt(0).toUpperCase() + severity.slice(1)}
                </Button>
              ))}
            </div>
            <Button
              variant={showAcknowledged ? "outline" : "secondary"}
              size="sm"
              onClick={() => setShowAcknowledged(!showAcknowledged)}
            >
              {showAcknowledged ? "Hide" : "Show"} Acknowledged
            </Button>
          </div>
        </div>

        {/* Alerts List */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">
              {filteredAlerts.length} Alert{filteredAlerts.length !== 1 ? "s" : ""}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {filteredAlerts.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <CheckCircle className="h-16 w-16 text-green-500 mb-4" />
                <h3 className="text-lg font-medium">No Alerts Found</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  {filterSeverity !== "all" || !showAcknowledged
                    ? "Try adjusting your filters"
                    : "All audits are passing! Great job."}
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {filteredAlerts.map((alert, index) => (
                  <div key={alert.id}>
                    <div
                      className={`p-4 rounded-lg border ${
                        alert.acknowledged ? "bg-muted/30 opacity-60" : "bg-card"
                      }`}
                    >
                      <div className="flex items-start gap-4">
                        <div
                          className={`p-2 rounded-lg ${getSeverityColor(alert.severity)}`}
                        >
                          {getAlertIcon(alert.type)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-start justify-between gap-2">
                            <div>
                              <div className="flex items-center gap-2">
                                <h4 className="font-medium">
                                  {getTypeLabel(alert.type)}
                                </h4>
                                <Badge
                                  variant={
                                    alert.severity === "high"
                                      ? "destructive"
                                      : alert.severity === "medium"
                                      ? "default"
                                      : "secondary"
                                  }
                                  className="text-xs"
                                >
                                  {alert.severity}
                                </Badge>
                                {alert.acknowledged && (
                                  <Badge variant="outline" className="text-xs">
                                    Acknowledged
                                  </Badge>
                                )}
                              </div>
                              <p className="text-sm text-muted-foreground mt-0.5">
                                {alert.adName} • {alert.campaignName}
                              </p>
                            </div>
                            <span className="text-xs text-muted-foreground whitespace-nowrap">
                              {formatDistanceToNow(new Date(alert.createdAt), {
                                addSuffix: true,
                              })}
                            </span>
                          </div>
                          <p className="mt-2 text-sm">{alert.message}</p>
                          <div className="mt-2 p-2 bg-muted rounded text-sm">
                            <span className="font-medium">Recommendation: </span>
                            {alert.recommendation}
                          </div>
                          {!alert.acknowledged && (
                            <div className="mt-3">
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleAcknowledge(alert.id)}
                              >
                                <CheckCircle className="h-4 w-4 mr-1" />
                                Acknowledge
                              </Button>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                    {index < filteredAlerts.length - 1 && (
                      <Separator className="my-4" />
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
