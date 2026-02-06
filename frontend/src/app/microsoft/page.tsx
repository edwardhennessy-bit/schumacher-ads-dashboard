"use client";

import { Header } from "@/components/layout/Header";
import { Monitor } from "lucide-react";

export default function MicrosoftDashboardPage() {
  return (
    <div className="min-h-screen bg-background">
      <Header
        title="Microsoft Ads"
        subtitle="Microsoft Advertising Performance Overview"
        onRefresh={() => {}}
        isLoading={false}
        selectedPreset="last_30d"
        customRange={null}
        onPresetChange={() => {}}
        onCustomRangeChange={() => {}}
      />

      <div className="p-6">
        <div className="flex flex-col items-center justify-center py-24">
          <div className="rounded-full bg-blue-100 p-6 mb-6">
            <Monitor className="h-12 w-12 text-blue-600" />
          </div>
          <h2 className="text-2xl font-bold text-foreground mb-2">
            Microsoft Ads — Coming Soon
          </h2>
          <p className="text-muted-foreground text-center max-w-md mb-6">
            The Microsoft Advertising dashboard is being built. Once connected,
            you&apos;ll see Bing search ads performance data here — spend, leads,
            CPL, campaigns, and more.
          </p>
          <div className="rounded-lg border bg-card p-6 max-w-lg w-full">
            <h3 className="font-semibold mb-3">To enable Microsoft Ads:</h3>
            <ol className="list-decimal list-inside space-y-2 text-sm text-muted-foreground">
              <li>Connect the Microsoft Ads account in the MCP Gateway</li>
              <li>Add Microsoft Ads API credentials to the backend .env file</li>
              <li>The dashboard will automatically populate with live data</li>
            </ol>
          </div>
        </div>
      </div>
    </div>
  );
}
