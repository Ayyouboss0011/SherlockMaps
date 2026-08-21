"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { crawlerApi } from "@/lib/api";
import { EmailSendHistoryEntry } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface SendHistoryProps {
  refreshTrigger: number;
}

const STATUS_STYLES: Record<string, { className: string; label: string }> = {
  pending: {
    className: "bg-blue-500/10 text-blue-600 animate-pulse border-blue-500/20",
    label: "Pending",
  },
  sent: {
    className: "bg-emerald-500/10 text-emerald-600 border-emerald-500/20",
    label: "Sent",
  },
  failed: {
    className: "bg-red-500/10 text-red-600 border-red-500/20",
    label: "Failed",
  },
  cancelled: {
    className: "bg-gray-500/10 text-gray-500 border-gray-500/20",
    label: "Cancelled",
  },
};

export default function SendHistory({ refreshTrigger }: SendHistoryProps) {
  const [entries, setEntries] = useState<EmailSendHistoryEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [polling, setPolling] = useState(false);
  const [stopping, setStopping] = useState(false);
  const [clearing, setClearing] = useState(false);
  const hasLoadedOnce = useRef(false);

  const load = useCallback(async () => {
    try {
      const data = await crawlerApi.getSendHistory(100, 0);
      setEntries(data.history);
      setTotal(data.total);
      setError(null);
      const hasPending = data.history.some((e) => e.status === "pending");
      setPolling(hasPending);
    } catch (err: any) {
      setError(err.message || "Could not load send history.");
    } finally {
      setLoading(false);
      hasLoadedOnce.current = true;
    }
  }, []);

  useEffect(() => {
    load();
  }, [refreshTrigger, load]);

  useEffect(() => {
    if (!polling) return;
    const interval = setInterval(load, 3000);
    return () => clearInterval(interval);
  }, [polling, load]);

  const pendingHistoryIds = Array.from(
    new Set(entries.filter((e) => e.status === "pending").map((e) => e.history_id))
  );

  const handleStop = async () => {
    setStopping(true);
    try {
      for (const historyId of pendingHistoryIds) {
        try {
          await crawlerApi.cancelEmailSend(historyId);
        } catch {
          // batch may have already finished
        }
      }
      await load();
    } finally {
      setStopping(false);
    }
  };

  const handleClear = async () => {
    if (!window.confirm("Delete the entire send history? This cannot be undone.")) return;
    setClearing(true);
    try {
      await crawlerApi.clearSendHistory();
      await load();
    } catch (err: any) {
      setError(err.message || "Could not clear send history.");
    } finally {
      setClearing(false);
    }
  };

  const statusBadge = (status: string) => {
    const style = STATUS_STYLES[status] || {
      className: "bg-gray-500/10 text-gray-500 border-gray-500/20",
      label: status,
    };
    return (
      <Badge variant="secondary" className={`text-xs h-4 px-1.5 ${style.className}`}>
        {style.label}
      </Badge>
    );
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return "-";
    return new Date(dateStr).toLocaleString("en-US");
  };

  return (
    <Card className="border-border/40">
      <CardHeader>
        <div className="flex items-center justify-between gap-2">
          <div>
            <CardTitle className="text-sm font-medium">Send History</CardTitle>
            <CardDescription className="text-xs">
              Status of every email sent to crawled contacts.
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            {polling && (
              <Badge variant="secondary" className="text-xs h-5 bg-blue-500/10 text-blue-600 border-blue-500/20">
                <span className="inline-block w-1 h-1 rounded-full bg-blue-500 mr-1 animate-ping" />
                Sending...
              </Badge>
            )}
            {pendingHistoryIds.length > 0 && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleStop}
                disabled={stopping}
                className="h-7 text-xs gap-1 text-red-600 hover:text-red-700 border-red-500/30 hover:bg-red-50 dark:hover:bg-red-950/20"
              >
                {stopping ? (
                  <>
                    <span className="inline-block w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin" />
                    Stopping...
                  </>
                ) : (
                  <>
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0zM9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
                    </svg>
                    Stop Sending
                  </>
                )}
              </Button>
            )}
            <Button variant="outline" size="sm" onClick={load} className="h-7 text-xs gap-1">
              Refresh
            </Button>
            {total > 0 && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleClear}
                disabled={clearing}
                className="h-7 text-xs gap-1 text-red-600 hover:text-red-700 border-red-500/30 hover:bg-red-50 dark:hover:bg-red-950/20"
              >
                {clearing ? "Clearing..." : "Clear History"}
              </Button>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {error && (
          <div className="flex items-center gap-2 rounded-md border border-red-500/20 bg-red-500/5 px-3 py-2 text-xs text-red-600 mb-3">
            {error}
          </div>
        )}

        {loading && !hasLoadedOnce.current ? (
          <div className="flex items-center justify-center py-6">
            <div className="inline-block w-4 h-4 border-2 border-foreground border-t-transparent rounded-full animate-spin" />
            <span className="ml-2 text-xs text-muted-foreground">Loading history...</span>
          </div>
        ) : entries.length === 0 ? (
          <div className="text-center py-10 text-muted-foreground">
            <p className="text-xs">No emails sent yet.</p>
            <p className="text-xs mt-1">
              Start a send from the form above to see results here.
            </p>
          </div>
        ) : (
          <>
            <p className="text-xs text-muted-foreground mb-2">
              Showing {entries.length} of {total} entries
            </p>
            <div className="table-container max-h-96 overflow-auto rounded-md border border-border/40">
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-card">
                  <tr className="border-b border-border/40">
                    <th className="text-left font-medium text-muted-foreground px-2.5 py-2">Status</th>
                    <th className="text-left font-medium text-muted-foreground px-2.5 py-2">Email</th>
                    <th className="text-left font-medium text-muted-foreground px-2.5 py-2">Company</th>
                    <th className="text-left font-medium text-muted-foreground px-2.5 py-2">Sent At</th>
                    <th className="text-left font-medium text-muted-foreground px-2.5 py-2">Error</th>
                  </tr>
                </thead>
                <tbody>
                  {entries.map((entry) => (
                    <tr key={entry.id} className="border-b border-border/30 last:border-0">
                      <td className="px-2.5 py-2">{statusBadge(entry.status)}</td>
                      <td className="px-2.5 py-2 font-mono text-muted-foreground">{entry.email}</td>
                      <td className="px-2.5 py-2 max-w-[160px] truncate">{entry.company_name || "-"}</td>
                      <td className="px-2.5 py-2 text-muted-foreground">{formatDate(entry.sent_at)}</td>
                      <td className="px-2.5 py-2 text-muted-foreground max-w-[200px] truncate">
                        {entry.error || "-"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
