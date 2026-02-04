"use client";

import { useState, useEffect } from "react";
import { Header } from "@/components/layout/Header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  CheckCircle,
  XCircle,
  Settings,
  Database,
  Bell,
  Zap,
} from "lucide-react";
import { api, ApiStatus } from "@/lib/api";

export default function SettingsPage() {
  const [status, setStatus] = useState<ApiStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchStatus = async () => {
    setIsLoading(true);
    try {
      const data = await api.getStatus();
      setStatus(data);
    } catch (error) {
      console.log("API not available");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const StatusIndicator = ({ connected }: { connected: boolean }) => (
    <div className="flex items-center gap-2">
      {connected ? (
        <>
          <CheckCircle className="h-4 w-4 text-green-600" />
          <span className="text-sm text-green-600">Connected</span>
        </>
      ) : (
        <>
          <XCircle className="h-4 w-4 text-red-500" />
          <span className="text-sm text-red-500">Not Connected</span>
        </>
      )}
    </div>
  );

  return (
    <div className="min-h-screen bg-background">
      <Header title="Settings" subtitle="Dashboard Configuration" />

      <div className="p-6 space-y-6 max-w-4xl">
        {/* Connection Status */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Zap className="h-5 w-5" />
              Connection Status
            </CardTitle>
            <CardDescription>
              Current status of external service connections
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between py-2">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <svg
                    className="h-5 w-5 text-blue-600"
                    viewBox="0 0 24 24"
                    fill="currentColor"
                  >
                    <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
                  </svg>
                </div>
                <div>
                  <p className="font-medium">Meta Ads</p>
                  <p className="text-sm text-muted-foreground">
                    Schumacher Homes Account (ID: 142003632)
                  </p>
                </div>
              </div>
              <StatusIndicator connected={status?.meta_connected ?? false} />
            </div>

            <Separator />

            <div className="flex items-center justify-between py-2">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-100 rounded-lg">
                  <svg
                    className="h-5 w-5 text-purple-600"
                    viewBox="0 0 24 24"
                    fill="currentColor"
                  >
                    <path d="M12 2C6.477 2 2 6.477 2 12s4.477 10 10 10 10-4.477 10-10S17.523 2 12 2zm0 18c-4.411 0-8-3.589-8-8s3.589-8 8-8 8 3.589 8 8-3.589 8-8 8zm-1-13h2v6h-2zm0 8h2v2h-2z" />
                  </svg>
                </div>
                <div>
                  <p className="font-medium">Claude AI</p>
                  <p className="text-sm text-muted-foreground">
                    Smart audit & content analysis
                  </p>
                </div>
              </div>
              <StatusIndicator connected={status?.claude_connected ?? false} />
            </div>

            <Separator />

            <div className="flex items-center justify-between py-2">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-100 rounded-lg">
                  <Bell className="h-5 w-5 text-green-600" />
                </div>
                <div>
                  <p className="font-medium">Slack Notifications</p>
                  <p className="text-sm text-muted-foreground">
                    Alert notifications to Slack
                  </p>
                </div>
              </div>
              <StatusIndicator connected={status?.slack_connected ?? false} />
            </div>

            <Separator />

            <div className="flex items-center justify-between py-2">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-orange-100 rounded-lg">
                  <Database className="h-5 w-5 text-orange-600" />
                </div>
                <div>
                  <p className="font-medium">Database</p>
                  <p className="text-sm text-muted-foreground">
                    {status?.database_url || "SQLite (Local)"}
                  </p>
                </div>
              </div>
              <Badge variant="secondary">Local</Badge>
            </div>
          </CardContent>
        </Card>

        {/* Meta Ads Setup */}
        <Card>
          <CardHeader>
            <CardTitle>Meta Ads Account Setup</CardTitle>
            <CardDescription>
              Connect the Schumacher Homes Meta Ads account to enable live data
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
              <h4 className="font-medium text-yellow-800">Action Required</h4>
              <p className="text-sm text-yellow-700 mt-1">
                The Schumacher Homes Meta Ads account (ID: 142003632) needs to be added
                to the MCP Gateway to enable live data integration.
              </p>
              <div className="mt-3">
                <p className="text-sm text-yellow-700 font-medium">Steps to connect:</p>
                <ol className="text-sm text-yellow-700 mt-1 list-decimal list-inside space-y-1">
                  <li>Go to Meta Business Manager Settings</li>
                  <li>Navigate to Users &rarr; System Users (or connected app)</li>
                  <li>Add the MCP Gateway credentials to the &quot;142003632 - Schumacher Homes&quot; account</li>
                  <li>Grant at least Analyst-level access</li>
                </ol>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Audit Settings */}
        <Card>
          <CardHeader>
            <CardTitle>Audit Settings</CardTitle>
            <CardDescription>
              Configure automated audit behavior
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Audit Interval</p>
                <p className="text-sm text-muted-foreground">
                  How often to run automated audits
                </p>
              </div>
              <Badge variant="outline">Every 4 hours</Badge>
            </div>

            <Separator />

            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Spend Anomaly Threshold</p>
                <p className="text-sm text-muted-foreground">
                  Alert when spending changes by this percentage
                </p>
              </div>
              <Badge variant="outline">50%</Badge>
            </div>

            <Separator />

            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">URL Health Checks</p>
                <p className="text-sm text-muted-foreground">
                  Check destination URLs for errors
                </p>
              </div>
              <Badge className="bg-green-100 text-green-800">Enabled</Badge>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
