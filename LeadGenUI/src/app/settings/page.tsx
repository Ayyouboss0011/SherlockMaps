"use client";

import { useState, useEffect, useCallback } from "react";
import { crawlerApi } from "@/lib/api";
import { StatsResponse } from "@/lib/types";
import HeaderNav from "@/components/Shared/HeaderNav";
import SmtpSettingsForm from "@/components/Settings/SmtpSettingsForm";
import TemplateManager from "@/components/Settings/TemplateManager";

export default function SettingsPage() {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [crawlerOnline, setCrawlerOnline] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchStatus = useCallback(async () => {
    try {
      const data = await crawlerApi.getStats();
      setStats(data);
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

  return (
    <div className="min-h-screen bg-background">
      <HeaderNav crawlerOnline={crawlerOnline} stats={stats} />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-5">
        <div>
          <h1 className="text-base font-medium text-foreground">Settings</h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Configure the SMTP server and email templates used for sending.
          </p>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="inline-block w-5 h-5 border-2 border-foreground border-t-transparent rounded-full animate-spin" />
            <span className="ml-2 text-sm text-muted-foreground">Loading...</span>
          </div>
        ) : (
          <>
            <SmtpSettingsForm />
            <TemplateManager />
          </>
        )}
      </main>
    </div>
  );
}
