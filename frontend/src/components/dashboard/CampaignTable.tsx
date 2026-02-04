"use client";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Campaign, formatCurrency, formatNumber, formatPercent } from "@/lib/mock-data";

interface CampaignTableProps {
  campaigns: Campaign[];
  title?: string;
}

export function CampaignTable({
  campaigns,
  title = "Campaign Performance",
}: CampaignTableProps) {
  const getStatusBadge = (status: Campaign["status"]) => {
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
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="min-w-[200px]">Campaign</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Spend</TableHead>
                <TableHead className="text-right">Clicks</TableHead>
                <TableHead className="text-right">CTR</TableHead>
                <TableHead className="text-right bg-green-50 text-green-800 font-semibold">Leads</TableHead>
                <TableHead className="text-right bg-green-50 text-green-800 font-semibold">CPL</TableHead>
                <TableHead className="text-right bg-green-50 text-green-800 font-semibold">Lead Rate</TableHead>
                <TableHead className="text-right">Conv.</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {campaigns.map((campaign) => (
                <TableRow key={campaign.id} className="cursor-pointer hover:bg-muted/50">
                  <TableCell className="font-medium">
                    <div className="flex flex-col">
                      <span className="truncate max-w-[200px]">{campaign.name}</span>
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
                    {formatPercent(campaign.ctr)}
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
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}
