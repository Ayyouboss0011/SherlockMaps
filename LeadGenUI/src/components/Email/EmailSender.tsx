"use client";

import { useState, useEffect, useCallback } from "react";
import { crawlerApi } from "@/lib/api";
import { HistoryEntry, EmailTemplate, SmtpSettings } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface Recipient {
  email: string;
  company_name: string;
  company_website: string;
  company_address: string;
}

interface EmailSenderProps {
  onSendStarted: () => void;
}

export default function EmailSender({ onSendStarted }: EmailSenderProps) {
  const [jobs, setJobs] = useState<HistoryEntry[]>([]);
  const [templates, setTemplates] = useState<EmailTemplate[]>([]);
  const [smtp, setSmtp] = useState<SmtpSettings | null>(null);
  const [selectedJob, setSelectedJob] = useState<string>("");
  const [selectedTemplate, setSelectedTemplate] = useState<string>("");
  const [delaySeconds, setDelaySeconds] = useState(2);
  const [testMode, setTestMode] = useState(false);
  const [recipients, setRecipients] = useState<Recipient[]>([]);
  const [recipientsLoading, setRecipientsLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const load = useCallback(async () => {
    try {
      const [history, templateList, smtpSettings] = await Promise.all([
        crawlerApi.getCrawlHistory(100, 0),
        crawlerApi.getTemplates(),
        crawlerApi.getSmtpSettings(),
      ]);
      setJobs(history.jobs.filter((job) => job.status === "completed"));
      setTemplates(templateList);
      setSmtp(smtpSettings);
    } catch (err: any) {
      setError(err.message || "Could not load jobs or templates.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const loadRecipients = async (jobId: string) => {
    if (!jobId) {
      setRecipients([]);
      return;
    }
    setRecipientsLoading(true);
    setError(null);
    try {
      const data = await crawlerApi.getJobRecipients(jobId);
      setRecipients(data);
    } catch (err: any) {
      setError(err.message || "Could not load recipients.");
      setRecipients([]);
    } finally {
      setRecipientsLoading(false);
    }
  };

  const handleJobChange = (jobId: string) => {
    setSelectedJob(jobId);
    setRecipients([]);
    loadRecipients(jobId);
  };

  const handleSend = async () => {
    if (!selectedJob || !selectedTemplate) {
      setError("Please select a job and a template.");
      return;
    }
    if (recipients.length === 0) {
      setError("This job has no email recipients.");
      return;
    }
    setSending(true);
    setError(null);
    setMessage(null);
    try {
      const response = await crawlerApi.sendEmails(
        selectedJob,
        selectedTemplate,
        delaySeconds,
        testMode
      );
      setMessage({
        type: "success",
        text: testMode
          ? `Test run started: ${response.total_recipients} personalized emails will be sent to ${smtp?.test_recipient_email || "the test address"}.`
          : `Sending started: ${response.total_recipients} recipients in queue.`,
      });
      onSendStarted();
    } catch (err: any) {
      setError(err.message || "Could not start sending.");
    } finally {
      setSending(false);
    }
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return "-";
    return new Date(dateStr).toLocaleString("en-US");
  };

  if (loading) {
    return (
      <Card className="border-border/40">
        <CardContent className="p-4">
          <div className="flex items-center justify-center py-6">
            <div className="inline-block w-4 h-4 border-2 border-foreground border-t-transparent rounded-full animate-spin" />
            <span className="ml-2 text-xs text-muted-foreground">Loading...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-border/40">
      <CardHeader>
        <CardTitle className="text-sm font-medium">Send Emails</CardTitle>
        <CardDescription className="text-xs">
          Send an email template to all crawled contacts of a completed job.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && (
          <div className="flex items-center gap-2 rounded-md border border-red-500/20 bg-red-500/5 px-3 py-2 text-xs text-red-600">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <Label htmlFor="send-job" className="text-xs text-muted-foreground">
              Crawl Job
            </Label>
            <select
              id="send-job"
              value={selectedJob}
              onChange={(e) => handleJobChange(e.target.value)}
              className="h-9 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm transition-colors outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30"
            >
              <option value="" className="bg-background">Select a completed job...</option>
              {jobs.map((job) => (
                <option key={job.job_id} value={job.job_id} className="bg-background">
                  {job.prompt} ({job.results_count ?? 0} results, {formatDate(job.created_at)})
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="send-template" className="text-xs text-muted-foreground">
              Template
            </Label>
            <select
              id="send-template"
              value={selectedTemplate}
              onChange={(e) => setSelectedTemplate(e.target.value)}
              className="h-9 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm transition-colors outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30"
            >
              <option value="" className="bg-background">Select a template...</option>
              {templates.map((template) => (
                <option key={template.id} value={template.id} className="bg-background">
                  {template.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <Label htmlFor="send-delay" className="text-xs text-muted-foreground">
              Delay between emails (seconds)
            </Label>
            <Input
              id="send-delay"
              type="number"
              min={0}
              max={60}
              value={delaySeconds}
              onChange={(e) => setDelaySeconds(parseFloat(e.target.value) || 0)}
              className="h-9 text-sm"
            />
          </div>
          <div className="flex items-center pt-6">
            <button
              type="button"
              onClick={() => setTestMode(!testMode)}
              className={`
                relative inline-flex h-[22px] w-[42px] shrink-0 cursor-pointer items-center rounded-full transition-colors
                focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2
                ${testMode ? "bg-amber-500" : "bg-gray-300 dark:bg-gray-600"}
              `}
              aria-label="Toggle test run mode"
              aria-checked={testMode}
              role="switch"
            >
              <span
                className={`
                  pointer-events-none inline-block h-[18px] w-[18px] rounded-full bg-white shadow-md
                  transform transition-transform duration-150 ease-in-out
                  ${testMode ? "translate-x-[22px]" : "translate-x-[2px]"}
                `}
              />
            </button>
            <span className={`ml-2 text-xs font-medium select-none ${testMode ? "text-amber-500" : "text-gray-400"}`}>
              {testMode ? "Test run (send all to test email)" : "Real send"}
            </span>
          </div>

          {testMode && !smtp?.test_recipient_email?.trim() && (
            <div className="flex items-center gap-2 rounded-md border border-amber-500/20 bg-amber-500/5 px-3 py-2 text-xs text-amber-600">
              <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              No test recipient email configured. Add one in Settings &gt; SMTP Settings.
            </div>
          )}
        </div>

        {selectedTemplate && (
          <div className="rounded-lg border border-border/40 bg-muted/30 p-3 space-y-1">
            <p className="text-xs font-medium text-foreground">Template Preview</p>
            {(() => {
              const template = templates.find((t) => t.id === selectedTemplate);
              return template ? (
                <>
                  <p className="text-xs text-muted-foreground">
                    <span className="text-foreground">Subject:</span> {template.subject}
                  </p>
                  <p className="text-xs text-muted-foreground whitespace-pre-wrap line-clamp-3">
                    {template.body}
                  </p>
                </>
              ) : null;
            })()}
          </div>
        )}

        {/* Recipients preview */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium text-foreground">
              Recipients
              <Badge variant="secondary" className="ml-2 text-xs h-4">
                {recipientsLoading ? "..." : recipients.length}
              </Badge>
            </p>
          </div>

          {selectedJob && recipientsLoading ? (
            <div className="flex items-center justify-center py-4">
              <div className="inline-block w-4 h-4 border-2 border-foreground border-t-transparent rounded-full animate-spin" />
            </div>
          ) : !selectedJob ? (
            <p className="text-xs text-muted-foreground py-2">
              Select a job to preview recipients.
            </p>
          ) : recipients.length === 0 ? (
            <p className="text-xs text-muted-foreground py-2">
              No email addresses found in this job.
            </p>
          ) : (
            <div className="max-h-48 overflow-auto rounded-md border border-border/40">
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-card">
                  <tr className="border-b border-border/40">
                    <th className="text-left font-medium text-muted-foreground px-2.5 py-1.5">Email</th>
                    <th className="text-left font-medium text-muted-foreground px-2.5 py-1.5">Company</th>
                  </tr>
                </thead>
                <tbody>
                  {recipients.map((recipient, idx) => (
                    <tr key={idx} className="border-b border-border/30 last:border-0">
                      <td className="px-2.5 py-1.5 font-mono text-muted-foreground">{recipient.email}</td>
                      <td className="px-2.5 py-1.5">{recipient.company_name || "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {message && (
          <div className={`flex items-center gap-2 rounded-md border px-3 py-2 text-xs ${
            message.type === "success"
              ? "border-emerald-500/20 bg-emerald-500/5 text-emerald-600"
              : "border-red-500/20 bg-red-500/5 text-red-600"
          }`}>
            {message.text}
          </div>
        )}

        <div className="flex justify-end">
          <Button
            type="button"
            onClick={handleSend}
            disabled={sending || !selectedJob || !selectedTemplate || recipients.length === 0 || (testMode && !smtp?.test_recipient_email?.trim())}
            className="h-8 text-xs gap-1.5"
          >
            {sending ? (
              <>
                <span className="inline-block w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin" />
                Starting...
              </>
            ) : (
              <>
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
                {testMode ? "Start Test Run" : "Send Emails"}
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
