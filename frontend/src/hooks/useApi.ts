"use client";

import { useState, useEffect, useCallback } from "react";
import {
  api,
  MetricsOverview,
  DailyMetric,
  Campaign,
  AuditAlert,
  AuditSummary,
} from "@/lib/api";

// Generic hook for API calls
function useApiCall<T>(
  fetcher: () => Promise<T>,
  deps: unknown[] = []
): {
  data: T | null;
  loading: boolean;
  error: Error | null;
  refetch: () => void;
} {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetcher();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err : new Error("Unknown error"));
    } finally {
      setLoading(false);
    }
  }, deps);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { data, loading, error, refetch: fetch };
}

// Metrics hooks
export function useMetricsOverview() {
  return useApiCall<MetricsOverview>(() => api.getMetricsOverview(), []);
}

export function useTrendData(days: number = 30) {
  return useApiCall<DailyMetric[]>(() => api.getTrendData(days), [days]);
}

export function useAdInventory() {
  return useApiCall(() => api.getAdInventory(), []);
}

// Campaign hooks
export function useCampaigns() {
  return useApiCall<Campaign[]>(() => api.getCampaigns(), []);
}

export function useCampaign(id: string) {
  return useApiCall<Campaign>(() => api.getCampaign(id), [id]);
}

// Audit hooks
export function useAlerts(params?: { severity?: string; acknowledged?: boolean }) {
  return useApiCall<AuditAlert[]>(
    () => api.getAlerts(params),
    [params?.severity, params?.acknowledged]
  );
}

export function useAuditSummary() {
  return useApiCall<AuditSummary>(() => api.getAuditSummary(), []);
}

// Combined dashboard data hook
export function useDashboardData() {
  const metrics = useMetricsOverview();
  const trends = useTrendData(30);
  const campaigns = useCampaigns();
  const alerts = useAlerts();

  const loading =
    metrics.loading || trends.loading || campaigns.loading || alerts.loading;

  const error = metrics.error || trends.error || campaigns.error || alerts.error;

  const refetchAll = useCallback(() => {
    metrics.refetch();
    trends.refetch();
    campaigns.refetch();
    alerts.refetch();
  }, [metrics, trends, campaigns, alerts]);

  return {
    metrics: metrics.data,
    trends: trends.data,
    campaigns: campaigns.data,
    alerts: alerts.data,
    loading,
    error,
    refetch: refetchAll,
  };
}
