"use client";

import { useState, useEffect } from "react";
import { Header } from "@/components/layout/Header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import {
  Eye,
  TrendingUp,
  TrendingDown,
  Minus,
  UserPlus,
} from "lucide-react";
import { api, Campaign } from "@/lib/api";
import { mockCampaigns, formatCurrency, formatNumber, formatPercent } from "@/lib/mock-data";

function transformCampaign(c: Campaign) {
  return {
    id: c.id,
    name: c.name,
    status: c.status,
    objective: c.objective,
    spend: c.spend,
    impressions: c.impressions,
    clicks: c.clicks,
    ctr: c.ctr,
    cpc: c.cpc,
    conversions: c.conversions,
    costPerConversion: c.cost_per_conversion,
    leads: c.leads,
    costPerLead: c.cost_per_lead,
    leadRate: c.lead_rate,
  };
}

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState(mockCampaigns);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedCampaign, setSelectedCampaign] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>("all");

  const fetchCampaigns = async () => {
    setIsLoading(true);
    try {
      const data = await api.getCampaigns();
      setCampaigns(data.map(transformCampaign));
    } catch (error) {
      console.log("API not available, using mock data");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchCampaigns();
  }, []);

  const filteredCampaigns = campaigns.filter((c) => {
    if (filterStatus === "all") return true;
    return c.status === filterStatus;
  });

  const totalSpend = filteredCampaigns.reduce((sum, c) => sum + c.spend, 0);
  const totalLeads = filteredCampaigns.reduce((sum, c) => sum + c.leads, 0);
  const totalConversions = filteredCampaigns.reduce((sum, c) => sum + c.conversions, 0);
  const avgCostPerLead = totalLeads > 0 ? totalSpend / totalLeads : 0;

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "ACTIVE":
        return <Badge className="bg-green-100 text-green-800 hover:bg-green-100">Active</Badge>;
      case "PAUSED":
        return <Badge variant="secondary">Paused</Badge>;
      case "ARCHIVED":
        return <Badge variant="outline">Archived</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <Header
        title="Campaigns"
        subtitle="All Meta Ads Campaigns"
        onRefresh={fetchCampaigns}
        isLoading={isLoading}
      />

      <div className="p-6 space-y-6">
        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total Spend
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatCurrency(totalSpend)}</div>
            </CardContent>
          </Card>
          <Card className="border-2 border-green-200 bg-green-50/50">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-green-800 flex items-center gap-1">
                <UserPlus className="h-4 w-4" />
                Total Leads
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-700">{formatNumber(totalLeads)}</div>
            </CardContent>
          </Card>
          <Card className="border-2 border-green-200 bg-green-50/50">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-green-800">
                Avg. Cost per Lead
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-700">{formatCurrency(avgCostPerLead)}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total Conversions
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatNumber(totalConversions)}</div>
            </CardContent>
          </Card>
        </div>

        {/* Filter Tabs */}
        <div className="flex gap-2">
          {["all", "ACTIVE", "PAUSED", "ARCHIVED"].map((status) => (
            <Button
              key={status}
              variant={filterStatus === status ? "default" : "outline"}
              size="sm"
              onClick={() => setFilterStatus(status)}
            >
              {status === "all" ? "All" : status.charAt(0) + status.slice(1).toLowerCase()}
              {status !== "all" && (
                <span className="ml-1 text-xs">
                  ({campaigns.filter((c) => c.status === status).length})
                </span>
              )}
            </Button>
          ))}
        </div>

        {/* Campaigns Table */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">
              {filteredCampaigns.length} Campaign{filteredCampaigns.length !== 1 ? "s" : ""}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="min-w-[250px]">Campaign</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Spend</TableHead>
                    <TableHead className="text-right">Clicks</TableHead>
                    <TableHead className="text-right">CTR</TableHead>
                    <TableHead className="text-right bg-green-50 text-green-800 font-semibold">Leads</TableHead>
                    <TableHead className="text-right bg-green-50 text-green-800 font-semibold">CPL</TableHead>
                    <TableHead className="text-right bg-green-50 text-green-800 font-semibold">Lead Rate</TableHead>
                    <TableHead className="text-right">Conv.</TableHead>
                    <TableHead className="text-center">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredCampaigns.map((campaign) => (
                    <TableRow
                      key={campaign.id}
                      className={`cursor-pointer hover:bg-muted/50 ${
                        selectedCampaign === campaign.id ? "bg-muted" : ""
                      }`}
                      onClick={() => setSelectedCampaign(campaign.id)}
                    >
                      <TableCell>
                        <div className="flex flex-col">
                          <span className="font-medium">{campaign.name}</span>
                          <span className="text-xs text-muted-foreground">
                            {campaign.objective.replace(/_/g, " ")}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell>{getStatusBadge(campaign.status)}</TableCell>
                      <TableCell className="text-right font-medium">
                        {formatCurrency(campaign.spend)}
                      </TableCell>
                      <TableCell className="text-right">
                        {formatNumber(campaign.clicks)}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          {campaign.ctr > 1.5 ? (
                            <TrendingUp className="h-3 w-3 text-green-600" />
                          ) : campaign.ctr < 1.2 ? (
                            <TrendingDown className="h-3 w-3 text-red-600" />
                          ) : (
                            <Minus className="h-3 w-3 text-muted-foreground" />
                          )}
                          {formatPercent(campaign.ctr)}
                        </div>
                      </TableCell>
                      <TableCell className="text-right font-semibold text-green-700 bg-green-50/50">
                        {campaign.leads}
                      </TableCell>
                      <TableCell className="text-right font-semibold text-green-700 bg-green-50/50">
                        {formatCurrency(campaign.costPerLead)}
                      </TableCell>
                      <TableCell className="text-right font-semibold text-green-700 bg-green-50/50">
                        {formatPercent(campaign.leadRate)}
                      </TableCell>
                      <TableCell className="text-right">
                        {campaign.conversions}
                      </TableCell>
                      <TableCell className="text-center">
                        <Button variant="ghost" size="sm">
                          <Eye className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
