"use client";

import { useState, useEffect, useCallback } from "react";
import { crawlerApi } from "@/lib/api";
import { StatsResponse, StatusResponse } from "@/lib/types";
import DashboardStats from "@/components/Dashboard/DashboardStats";
import CrawlForm from "@/components/Crawl/CrawlForm";
import CombinedTable from "@/components/Combined/CombinedTable";
import HeaderNav from "@/components/Shared/HeaderNav";

export default function Home() {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [crawlerOnline, setCrawlerOnline] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [loading, setLoading] = useState(true);

  const fetchStatus = useCallback(async () => {
    try {
      const [statsData, statusData] = await Promise.all([
        crawlerApi.getStats(),
        crawlerApi.getStatus(),
      ]);
      setStats(statsData);
      setStatus(statusData);
      setCrawlerOnline(true);
    } catch {
      setCrawlerOnline(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 10000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  const handleCrawlStarted = () => {
    setRefreshTrigger((prev) => prev + 1);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center space-y-3">
          <div className="inline-block w-5 h-5 border-2 border-foreground border-t-transparent rounded-full animate-spin" />
          <p className="text-muted-foreground text-sm">Loading SherlockMaps...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <HeaderNav crawlerOnline={crawlerOnline} stats={stats} />

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-5">
        {/* Dashboard Stats */}
        <DashboardStats
          status={status}
          stats={stats}
          crawlerOnline={crawlerOnline}
        />

        {/* Crawl Form */}
        <CrawlForm
          onCrawlStarted={handleCrawlStarted}
          onError={() => {}}
        />

        {/* Combined Jobs & Results Table */}
        <CombinedTable refreshTrigger={refreshTrigger} />
      </main>

      {/* Footer */}
      <footer className="border-t border-border/50 mt-8 py-3">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>SherlockMaps</span>
            <span>
              {process.env.NEXT_PUBLIC_CRAWLER_API_URL || "http://localhost:8000"}
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}