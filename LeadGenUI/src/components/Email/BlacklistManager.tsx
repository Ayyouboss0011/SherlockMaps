"use client";

import { useState, useRef, type ChangeEvent } from "react";
import { crawlerApi } from "@/lib/api";
import { EmailBlacklistEntry } from "@/lib/types";
import CollapsibleCard from "@/components/Shared/CollapsibleCard";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface BlacklistManagerProps {
  blacklist: EmailBlacklistEntry[];
  onBlacklistChange: (entries: EmailBlacklistEntry[]) => void;
}

function parseEmails(text: string): string[] {
  return text
    .split(/[\n,;]+/)
    .map((e) => e.trim())
    .filter((e) => e.length > 0);
}

export default function BlacklistManager({ blacklist, onBlacklistChange }: BlacklistManagerProps) {
  const [emailsText, setEmailsText] = useState("");
  const [note, setNote] = useState("");
  const [adding, setAdding] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [removingEmail, setRemovingEmail] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [importing, setImporting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const refresh = async () => {
    try {
      const data = await crawlerApi.getBlacklist();
      onBlacklistChange(data.entries);
    } catch (err: any) {
      setError(err.message || "Could not load blacklist.");
    }
  };

  const handleAdd = async () => {
    const emails = parseEmails(emailsText);
    if (emails.length === 0) {
      setError("Enter at least one email address.");
      return;
    }
    setAdding(true);
    setError(null);
    setMessage(null);
    try {
      const result = await crawlerApi.addToBlacklist(emails, note);
      const parts: string[] = [];
      if (result.added.length > 0) parts.push(`${result.added.length} added`);
      if (result.skipped.length > 0) parts.push(`${result.skipped.length} already blacklisted or invalid`);
      setMessage({ type: "success", text: parts.join(", ") + "." });
      setEmailsText("");
      setNote("");
      await refresh();
    } catch (err: any) {
      setError(err.message || "Could not add to blacklist.");
    } finally {
      setAdding(false);
    }
  };

  const handleRemove = async (email: string) => {
    setRemovingEmail(email);
    setError(null);
    try {
      await crawlerApi.removeFromBlacklist(email);
      await refresh();
    } catch (err: any) {
      setError(err.message || "Could not remove from blacklist.");
    } finally {
      setRemovingEmail(null);
    }
  };

  const handleClear = async () => {
    if (!window.confirm("Remove ALL entries from the blacklist? These contacts could receive emails again.")) return;
    setClearing(true);
    setError(null);
    try {
      await crawlerApi.clearBlacklist();
      await refresh();
    } catch (err: any) {
      setError(err.message || "Could not clear blacklist.");
    } finally {
      setClearing(false);
    }
  };

  const handleFileSelected = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const name = file.name.toLowerCase();
    if (!name.endsWith(".xlsx") && !name.endsWith(".csv")) {
      setError("Please choose an .xlsx or .csv file.");
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }
    setImporting(true);
    setError(null);
    setMessage(null);
    try {
      const result = await crawlerApi.importBlacklistFile(file);
      const parts: string[] = [`Found ${result.emails_found} email(s) in ${result.filename}:`];
      if (result.total_added > 0) parts.push(`${result.total_added} added`);
      if (result.skipped.length > 0) parts.push(`${result.skipped.length} already blacklisted`);
      setMessage({ type: "success", text: parts.join(", ") + "." });
      await refresh();
    } catch (err: any) {
      setError(err.message || "Could not import the file.");
    } finally {
      setImporting(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return "-";
    return new Date(dateStr).toLocaleString("en-US");
  };

  return (
    <CollapsibleCard
      title={
        <>
          Email Blacklist
          <Badge variant="secondary" className="ml-2 text-xs h-4">{blacklist.length}</Badge>
        </>
      }
      description="Do-not-contact list: blacklisted emails are never emailed. Add contacts here who told you they don't want to hear from you."
      actions={
        blacklist.length > 0 ? (
          <Button
            variant="outline"
            size="sm"
            onClick={handleClear}
            disabled={clearing}
            className="h-7 text-xs gap-1 text-red-600 hover:text-red-700 border-red-500/30 hover:bg-red-50 dark:hover:bg-red-950/20"
          >
            {clearing ? "Clearing..." : "Clear All"}
          </Button>
        ) : undefined
      }
      storageKey="leadgen.card.blacklist"
      contentClassName="space-y-4"
    >
        {error && (
          <div className="flex items-center gap-2 rounded-md border border-red-500/20 bg-red-500/5 px-3 py-2 text-xs text-red-600">
            {error}
          </div>
        )}
        {message && (
          <div className={`flex items-center gap-2 rounded-md border px-3 py-2 text-xs ${
            message.type === "success"
              ? "border-emerald-500/20 bg-emerald-500/5 text-emerald-600"
              : "border-red-500/20 bg-red-500/5 text-red-600"
          }`}>
            {message.text}
          </div>
        )}

        {/* Add form */}
        <div className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="blacklist-emails" className="text-xs text-muted-foreground">
              Email addresses (one per line, or separated by commas)
            </Label>
            <textarea
              id="blacklist-emails"
              value={emailsText}
              onChange={(e) => setEmailsText(e.target.value)}
              placeholder={"max@firma.de\nanna@beispiel.com"}
              rows={3}
              className="flex w-full rounded-lg border border-input bg-transparent px-2.5 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30"
            />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-[1fr_auto] gap-3 items-end">
            <div className="space-y-1.5">
              <Label htmlFor="blacklist-note" className="text-xs text-muted-foreground">
                Reason (optional)
              </Label>
              <Input
                id="blacklist-note"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="e.g. unsubscribed, requested no contact"
                className="h-9 text-sm"
              />
            </div>
            <Button
              type="button"
              onClick={handleAdd}
              disabled={adding || parseEmails(emailsText).length === 0}
              className="h-9 text-xs gap-1.5"
            >
              {adding ? (
                <>
                  <span className="inline-block w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin" />
                  Adding...
                </>
              ) : (
                <>
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.5v15m7.5-7.5h-15" />
                  </svg>
                  Add to Blacklist
                </>
              )}
            </Button>
          </div>
        </div>

        {/* File import */}
        <div className="rounded-lg border border-dashed border-border/60 bg-muted/20 p-3 space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <svg className="w-4 h-4 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p className="text-xs text-muted-foreground">
                Or import from an <span className="font-medium text-foreground">Excel (.xlsx) or CSV file</span> -
                email addresses are detected automatically, no specific column layout needed.
              </p>
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx,.csv"
              onChange={handleFileSelected}
              className="hidden"
            />
            <Button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={importing}
              className="h-8 text-xs gap-1.5"
            >
              {importing ? (
                <>
                  <span className="inline-block w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin" />
                  Importing...
                </>
              ) : (
                <>
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M12 4v12m0-12l-4 4m4-4l4 4" />
                  </svg>
                  Upload File
                </>
              )}
            </Button>
          </div>
        </div>

        {/* Entries */}
        {blacklist.length === 0 ? (
          <p className="text-xs text-muted-foreground py-2">
            The blacklist is empty. Everyone you crawl can receive emails.
          </p>
        ) : (
          <div className="max-h-64 overflow-auto rounded-md border border-border/40">
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-card">
                <tr className="border-b border-border/40">
                  <th className="text-left font-medium text-muted-foreground px-2.5 py-1.5">Email</th>
                  <th className="text-left font-medium text-muted-foreground px-2.5 py-1.5">Reason</th>
                  <th className="text-left font-medium text-muted-foreground px-2.5 py-1.5">Added</th>
                  <th className="text-right font-medium text-muted-foreground px-2.5 py-1.5">Remove</th>
                </tr>
              </thead>
              <tbody>
                {blacklist.map((entry) => (
                  <tr key={entry.email} className="border-b border-border/30 last:border-0">
                    <td className="px-2.5 py-1.5 font-mono">{entry.email}</td>
                    <td className="px-2.5 py-1.5 text-muted-foreground max-w-[200px] truncate">{entry.note || "-"}</td>
                    <td className="px-2.5 py-1.5 text-muted-foreground">{formatDate(entry.added_at)}</td>
                    <td className="px-2.5 py-1.5 text-right">
                      <button
                        type="button"
                        onClick={() => handleRemove(entry.email)}
                        disabled={removingEmail === entry.email}
                        className="rounded p-1 text-muted-foreground hover:text-red-600 hover:bg-red-500/10 disabled:opacity-50"
                        title="Remove from blacklist"
                        aria-label={`Remove ${entry.email} from blacklist`}
                      >
                        {removingEmail === entry.email ? (
                          <span className="inline-block w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin" />
                        ) : (
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        )}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
    </CollapsibleCard>
  );
}
