"use client";

import { StatsResponse, StatusResponse } from "@/lib/types";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface DashboardStatsProps {
  status: StatusResponse | null;
  stats: StatsResponse | null;
  crawlerOnline: boolean;
}

export default function DashboardStats({
  status,
  stats,
  crawlerOnline,
}: DashboardStatsProps) {
  const isRunning = status?.status === "busy";

  const statItems = [
    {
      label: "Crawler",
      value: crawlerOnline ? "Online" : "Offline",
      dotColor: crawlerOnline ? "bg-emerald-500" : "bg-red-500",
      valueColor: crawlerOnline ? "text-emerald-600" : "text-red-600",
    },
    {
      label: "Status",
      value: isRunning ? "Running" : crawlerOnline ? "Ready" : "-",
      dotColor: isRunning ? "bg-amber-500" : crawlerOnline ? "bg-emerald-500" : "bg-muted",
      valueColor: isRunning
        ? "text-amber-600"
        : crawlerOnline
        ? "text-emerald-600"
        : "text-muted-foreground",
    },
    {
      label: "Pending",
      value: String(stats?.total_pending ?? 0),
      dotColor: "bg-transparent",
      valueColor: (stats?.total_pending && stats.total_pending > 0) ? "text-amber-600" : "text-foreground",
    },
    {
      label: "Companies",
      value: String(stats?.total_companies_found ?? 0),
      dotColor: "bg-transparent",
      valueColor: "text-foreground",
    },
    {
      label: "Emails Found",
      value: String(stats?.total_emails_found ?? 0),
      dotColor: "bg-transparent",
      valueColor: "text-blue-600 font-semibold",
    },
    {
      label: "Crawls",
      value: String(stats?.total_crawls ?? 0),
      dotColor: "bg-transparent",
      valueColor: "text-foreground",
    },
    {
      label: "Errors",
      value: String(stats?.total_failed ?? 0),
      dotColor: "bg-transparent",
      valueColor: "text-red-600",
    },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-7 gap-3">
      {statItems.map((item, index) => (
        <Card key={index} className="border-border/40">
          <CardContent className="p-3">
            <span className="text-xs text-muted-foreground block mb-1.5">{item.label}</span>
            <span className={cn("text-lg font-medium", item.valueColor)}>
              {isRunning && item.value === "Running" ? (
                <span className="flex items-center gap-2">
                  <span className="inline-block w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin" />
                  {item.value}
                </span>
              ) : (
                item.value
              )}
            </span>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}