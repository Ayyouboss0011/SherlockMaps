"use client";

import { useState, useEffect, useCallback, Fragment } from "react";
import { crawlerApi } from "@/lib/api";
import { HistoryEntry, CompanyData, ReviewData, EmailCrawlStatus } from "@/lib/types";
import StatusBadge from "@/components/Shared/StatusBadge";
import { Card, CardContent } from "@/components/ui/card";
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
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";

interface CombinedTableProps {
  refreshTrigger: number;
}

export default function CombinedTable({ refreshTrigger }: CombinedTableProps) {
  const [jobs, setJobs] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [pollingActive, setPollingActive] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  // Expanded job IDs
  const [expandedJobs, setExpandedJobs] = useState<Set<string>>(new Set());

  // Results data per job
  const [jobResults, setJobResults] = useState<Record<string, CompanyData[]>>({});
  const [resultsLoading, setResultsLoading] = useState<string | null>(null);

  // Email dialog state
  const [emailDialogOpen, setEmailDialogOpen] = useState(false);
  const [emailJobId, setEmailJobId] = useState<string | null>(null);
  const [emailsData, setEmailsData] = useState<any[]>([]);
  const [emailsLoading, setEmailsLoading] = useState(false);
  const [emailsError, setEmailsError] = useState<string | null>(null);
  const [parentJobId, setParentJobId] = useState<string | null>(null);

  // Search within results
  const [searchTerm, setSearchTerm] = useState("");

  const hasActiveJobs = jobs.some(
    (job) => job.status === "pending" || job.status === "running"
  );

  // Check if any completed job has companies with pending email status
  const hasPendingEmailCrawls = jobs.some(
    (job) =>
      job.status === "completed" &&
      (jobResults[job.job_id] || []).some(
        (company) => company.email_status === "pending"
      )
  );

  // Check if any completed job has an active email crawl (email_job_status is running/pending)
  const hasActiveEmailJobs = jobs.some(
    (job) => job.email_job_status === "running" || job.email_job_status === "pending"
  );

  const isPollingActive = hasActiveJobs || hasPendingEmailCrawls || hasActiveEmailJobs;

  const loadJobs = useCallback(async () => {
    try {
      setApiError(null);
      const data = await crawlerApi.getCrawlHistory(50, 0);
      setJobs(data.jobs);
    } catch (err: any) {
      const errorMsg = err.message || "API unreachable";
      console.error("Failed to load crawl history:", err);
      setApiError(errorMsg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadJobs();
  }, [refreshTrigger, loadJobs]);

  useEffect(() => {
    if (isPollingActive && !pollingActive) {
      setPollingActive(true);
    } else if (!isPollingActive && pollingActive) {
      setPollingActive(false);
    }
  }, [isPollingActive, pollingActive]);

  useEffect(() => {
    if (!pollingActive) return;

    const interval = setInterval(async () => {
      await loadJobs();
    }, 3000);

    return () => clearInterval(interval);
  }, [pollingActive, loadJobs]);

  const toggleJobExpansion = async (jobId: string) => {
    const newExpanded = new Set(expandedJobs);

    if (newExpanded.has(jobId)) {
      newExpanded.delete(jobId);
      setExpandedJobs(newExpanded);
    } else {
      newExpanded.add(jobId);
      setExpandedJobs(newExpanded);

      // Load results if not already loaded
      if (!jobResults[jobId] && !resultsLoading) {
        await loadJobResults(jobId);
      }
    }
  };

  const loadJobResults = async (jobId: string) => {
    setResultsLoading(jobId);
    try {
      const data = await crawlerApi.getJobResults(jobId);
      console.log("=== API Response for job", jobId, "===");
      console.log("Full response:", JSON.stringify(data, null, 2));
      console.log("data.results:", data.results);
      console.log("data.results type:", typeof data.results, Array.isArray(data.results));
      
      // Try multiple possible field names for results
      const raw = data as any;
      let results: CompanyData[] = [];
      
      if (Array.isArray(data.results) && data.results.length > 0) {
        results = data.results;
      } else if (Array.isArray(raw.data) && raw.data.length > 0) {
        results = raw.data;
      } else if (Array.isArray(raw.companies) && raw.companies.length > 0) {
        results = raw.companies;
      } else if (Array.isArray(raw.items) && raw.items.length > 0) {
        results = raw.items;
      } else {
        // If results field exists but is empty, check if it's an object with nested results
        if (raw?.results && typeof raw.results === 'object' && !Array.isArray(raw.results)) {
          console.log("Results is an object, checking for nested arrays...");
          console.log("Results keys:", Object.keys(raw.results));
          // Check common nested patterns
          for (const key of Object.keys(raw.results)) {
            if (Array.isArray(raw.results[key])) {
              results = raw.results[key];
              console.log(`Found array in results.${key}:`, results.length, "items");
              break;
            }
          }
        }
      }
      
      console.log("Extracted results count:", results.length);
      if (results.length > 0) {
        console.log("First result sample:", results[0]);
      }
      
      setJobResults((prev) => ({ ...prev, [jobId]: results }));
    } catch (err: any) {
      console.error(`Failed to load results for job ${jobId}:`, err);
      setJobResults((prev) => ({ ...prev, [jobId]: [] }));
    } finally {
      setResultsLoading(null);
    }
  };

  const handleStartEmailCrawl = async (jobId: string) => {
    try {
      await crawlerApi.startEmailCrawl(jobId);
      await loadJobs();
    } catch (err) {
      console.error("Failed to start email crawl:", err);
    }
  };

  const viewEmails = async (jobId: string) => {
    setEmailDialogOpen(true);
    setEmailJobId(jobId);
    setEmailsLoading(true);
    setEmailsError(null);
    setEmailsData([]);
    setParentJobId(null);

    try {
      const emailJob = await crawlerApi.getEmailJobByParent(jobId);
      if (!emailJob) {
        setEmailsError("No email crawl found for this job.");
        setEmailsData([]);
        return;
      }

      setParentJobId(emailJob.job_id);

      // Fetch emails from the email job results
      const emailJobData = await crawlerApi.getJobResults(emailJob.job_id);
      const results = (emailJobData.results as any[]) || [];
      setEmailsData(results);
    } catch (err: any) {
      setEmailsError(err.message || "Could not load emails.");
      setEmailsData([]);
    } finally {
      setEmailsLoading(false);
    }
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return "-";
    return new Date(dateStr).toLocaleString("en-US");
  };

  const handleCopyEmail = (email: string) => {
    navigator.clipboard.writeText(email);
  };

  // Aggregate all emails from company results for a job
  const getAllEmailsFromResults = (results: CompanyData[]): { email: string; company: string; url?: string }[] => {
    const allEmails: { email: string; company: string; url?: string }[] = [];
    for (const company of results) {
      const companyEmails = company.emails || [];
      const companyName = company.name || company.company_name || "-";
      const companyUrl = company.website || "";
      for (const email of companyEmails) {
        allEmails.push({ email, company: companyName, url: companyUrl });
      }
    }
    return allEmails;
  };

  const handleCopyAllEmails = () => {
    const allEmails = emailsData.map((e) => e.email || e.Email || "-").join("\n");
    navigator.clipboard.writeText(allEmails);
  };

  // Helper to get email status badge
  const getEmailStatusBadge = (status?: EmailCrawlStatus) => {
    if (!status || status === "not_started") {
      return <Badge variant="secondary" className="bg-gray-500/10 text-gray-500 text-xs border-gray-500/20 h-4 px-1.5">Not Started</Badge>;
    }
    if (status === "pending") {
      return (
        <Badge variant="secondary" className="bg-blue-500/10 text-blue-600 animate-pulse text-xs border-blue-500/20 h-4 px-1.5">
          <span className="inline-block w-1 h-1 rounded-full bg-blue-500 mr-1 animate-ping" />
          Crawling
        </Badge>
      );
    }
    if (status === "completed") {
      return <Badge variant="secondary" className="bg-emerald-500/10 text-emerald-600 text-xs border-emerald-500/20 h-4 px-1.5">Done</Badge>;
    }
    if (status === "failed") {
      return <Badge variant="secondary" className="bg-red-500/10 text-red-600 text-xs border-red-500/20 h-4 px-1.5">Failed</Badge>;
    }
    return "-";
  };

  // Filter results based on search
  const getFilteredResults = (jobId: string): CompanyData[] => {
    const results = jobResults[jobId] || [];
    if (!searchTerm.trim()) return results;
    const search = searchTerm.toLowerCase();
    return results.filter((row) =>
      Object.values(row).some((val) =>
        String(val ?? "").toLowerCase().includes(search)
      )
    );
  };

  if (loading) {
    return (
      <Card className="border-border/40">
        <CardContent className="p-4">
          <div className="flex items-center justify-center py-6">
            <div className="inline-block w-4 h-4 border-2 border-foreground border-t-transparent rounded-full animate-spin" />
            <span className="ml-2 text-xs text-muted-foreground">Loading jobs...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-border/40">
      <CardContent className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-medium text-foreground">
            Crawl Jobs & Results
            <Badge variant="secondary" className="ml-2 text-xs h-5">
              {jobs.length}
            </Badge>
          </h2>
        </div>

        {apiError && (
          <div className="flex items-start gap-2 rounded-md border border-red-500/20 bg-red-500/5 px-3 py-2 text-xs text-red-600">
            <svg className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="flex-1">
              <p className="font-medium">API Error</p>
              <p className="mt-1 opacity-80">{apiError}</p>
              <button
                onClick={loadJobs}
                className="underline mt-1 text-red-500 hover:text-red-600"
              >
                Try again
              </button>
            </div>
          </div>
        )}

        {jobs.length === 0 && !apiError ? (
          <div className="text-center py-10 text-muted-foreground">
            <p className="text-xs">No crawl jobs available yet.</p>
            <p className="text-xs mt-1 text-muted-foreground">
              Start a new crawl using the form above.
            </p>
          </div>
        ) : (
          <>
            {/* ===== MAIN JOBS TABLE ===== */}
            <div className="table-container">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-8"></TableHead>
                    <TableHead>Job ID</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Search Term</TableHead>
                    <TableHead className="text-center">Results</TableHead>
                    <TableHead className="text-center">Emails</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {jobs.map((job) => {
                    const isExpanded = expandedJobs.has(job.job_id);
                    const results = jobResults[job.job_id] || [];
                    const filteredResults = getFilteredResults(job.job_id);
                    const aggregatedEmails = getAllEmailsFromResults(results);

                    return (
                      <Fragment key={job.job_id}>
                        <TableRow
                          className={isExpanded ? "bg-muted/30" : ""}
                        >
                          <TableCell>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 w-6 p-0 hover:bg-muted"
                              onClick={() => toggleJobExpansion(job.job_id)}
                            >
                              <svg
                                className={`w-3.5 h-3.5 transition-transform ${isExpanded ? "rotate-180" : ""}`}
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                              >
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                              </svg>
                            </Button>
                          </TableCell>
                          <TableCell className="font-mono text-xs text-muted-foreground">
                            {job.job_id.substring(0, 8)}...
                          </TableCell>
                          <TableCell>
                            <StatusBadge status={job.status} />
                          </TableCell>
                          <TableCell className="max-w-xs truncate">
                            {job.prompt}
                          </TableCell>
                          <TableCell className="text-center">
                            {job.results_count ?? 0}
                          </TableCell>
                          <TableCell className="text-center">
                            {job.email_job_status === "completed" && (
                              <Badge variant="secondary" className="bg-emerald-500/10 text-emerald-600 hover:bg-emerald-500/20 text-xs border-emerald-500/20 h-5 px-1.5 font-medium">
                                {job.emails_found ?? 0} found
                              </Badge>
                            )}
                            {(job.email_job_status === "running" || job.email_job_status === "pending") && (
                              <Badge variant="secondary" className="bg-blue-500/10 text-blue-600 animate-pulse text-xs border-blue-500/20 h-5 px-1.5 font-medium">
                                <span className="inline-block w-1 h-1 rounded-full bg-blue-500 mr-1 animate-ping" />
                                {job.email_job_status === "running" ? "Crawling" : "Pending"}
                              </Badge>
                            )}
                            {job.email_job_status === "failed" && (
                              <Badge variant="secondary" className="bg-red-500/10 text-red-600 text-xs border-red-500/20 h-5 px-1.5 font-medium">
                                Failed
                              </Badge>
                            )}
                            {!job.email_job_status && job.status === "completed" && (
                              <Button
                                variant="outline"
                                size="sm"
                                className="h-5 px-1.5 text-[10px] gap-1 text-blue-600 hover:text-blue-700 hover:bg-blue-50 border-blue-200/50 dark:hover:bg-blue-955/20"
                                onClick={() => handleStartEmailCrawl(job.job_id)}
                              >
                                <svg className="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                                </svg>
                                Crawl
                              </Button>
                            )}
                            {!job.email_job_status && job.status !== "completed" && (
                              <span className="text-muted-foreground">-</span>
                            )}
                          </TableCell>
                          <TableCell className="text-muted-foreground text-xs">
                            {formatDate(job.created_at)}
                          </TableCell>
                          <TableCell>
                            <div className="flex gap-1.5">
                              {(job.status === "pending" || job.status === "running") && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-6 px-1.5 text-xs text-red-600 hover:text-red-700"
                                  onClick={async () => {
                                    try {
                                      await crawlerApi.cancelJob(job.job_id);
                                      await loadJobs();
                                    } catch (err) {
                                      console.error("Failed to cancel:", err);
                                    }
                                  }}
                                >
                                  Cancel
                                </Button>
                              )}
                            </div>
                          </TableCell>
                        </TableRow>

                        {/* Expanded row with company results */}
                        {isExpanded && (
                          <TableRow className="bg-muted/20 border-b">
                            <TableCell colSpan={8}>
                              <div className="p-3 space-y-3">
                                <div className="flex items-center justify-between">
                                  <h3 className="text-xs font-medium text-muted-foreground">
                                    Company Results: {job.prompt}
                                    <Badge variant="secondary" className="ml-2 text-xs h-4">
                                      {results.length}
                                    </Badge>
                                  </h3>
                                  {results.length > 0 && (
                                    <div className="relative max-w-xs">
                                      <svg
                                        className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground"
                                        fill="none"
                                        stroke="currentColor"
                                        viewBox="0 0 24 24"
                                      >
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                                      </svg>
                                      <Input
                                        type="text"
                                        value={searchTerm}
                                        onChange={(e) => setSearchTerm(e.target.value)}
                                        placeholder="Search results..."
                                        className="pl-8 h-7 text-xs bg-background"
                                      />
                                    </div>
                                  )}
                                </div>

                                {resultsLoading === job.job_id ? (
                                  <div className="flex items-center justify-center py-6">
                                    <div className="inline-block w-4 h-4 border-2 border-foreground border-t-transparent rounded-full animate-spin" />
                                    <span className="ml-2 text-xs text-muted-foreground">Loading results...</span>
                                  </div>
                                ) : results.length === 0 ? (
                                  <div className="text-center py-6 text-muted-foreground">
                                    <p className="text-xs">No results available for this job.</p>
                                  </div>
                                ) : (
                                  <div className="table-container max-h-96 overflow-auto rounded-md border border-border/40">
                                    <Table>
                                      <TableHeader className="sticky top-0 bg-card">
                                        <TableRow>
                                          <TableHead>Company</TableHead>
                                          <TableHead>Address</TableHead>
                                          <TableHead>Phone</TableHead>
                                          <TableHead>Website</TableHead>
                                          <TableHead>Email</TableHead>
                                          <TableHead>Email Status</TableHead>
                                          <TableHead>Category</TableHead>
                                          <TableHead>Rating</TableHead>
                                        </TableRow>
                                      </TableHeader>
                                      <TableBody>
                                        {filteredResults.map((row, idx) => (
                                          <TableRow key={idx}>
                                            <TableCell className="font-medium max-w-[180px] truncate text-xs">
                                              {row.name || row.company_name || "-"}
                                            </TableCell>
                                            <TableCell className="max-w-[180px] truncate text-xs">
                                              {row.address || "-"}
                                            </TableCell>
                                            <TableCell className="max-w-[120px] truncate text-xs">
                                              {row.phone || "-"}
                                            </TableCell>
                                            <TableCell className="max-w-[150px] text-xs">
                                              {row.website ? (
                                                <a
                                                  href={row.website}
                                                  target="_blank"
                                                  rel="noopener noreferrer"
                                                  className="text-blue-600 hover:text-blue-700 underline"
                                                >
                                                  {row.website}
                                                </a>
                                              ) : (
                                                "-"
                                              )}
                                            </TableCell>
                                            <TableCell className="max-w-[180px] truncate text-xs">
                                              {row.emails && row.emails.length > 0 ? (
                                                <div className="flex items-center gap-1">
                                                  <a
                                                    href={`mailto:${row.emails.join(",")}`}
                                                    className="text-blue-500 hover:underline font-mono text-[10px]"
                                                    title={row.emails.join(", ")}
                                                  >
                                                    {row.emails.join(", ")}
                                                  </a>
                                                  <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    className="h-4 w-4 p-0 hover:bg-muted"
                                                    onClick={() => handleCopyEmail(row.emails?.join(", ") || "")}
                                                    title="Copy emails"
                                                  >
                                                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                                                    </svg>
                                                  </Button>
                                                </div>
                                              ) : row.email ? (
                                                <div className="flex items-center gap-1">
                                                  <a
                                                    href={`mailto:${row.email}`}
                                                    className="text-blue-500 hover:underline font-mono"
                                                  >
                                                    {row.email}
                                                  </a>
                                                  <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    className="h-4 w-4 p-0 hover:bg-muted"
                                                    onClick={() => handleCopyEmail(row.email || "")}
                                                    title="Copy email"
                                                  >
                                                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                                                    </svg>
                                                  </Button>
                                                </div>
                                              ) : (
                                                "-"
                                              )}
                                            </TableCell>
                                            <TableCell className="text-xs">
                                              {getEmailStatusBadge(row.email_status)}
                                            </TableCell>
                                            <TableCell className="max-w-[100px] truncate text-xs">
                                              {row.category || "-"}
                                            </TableCell>
                                            <TableCell className="text-xs">
                                              {row.rating ? (
                                                <span className="flex items-center gap-0.5">
                                                  <svg
                                                    className="w-3 h-3 text-yellow-500"
                                                    fill="currentColor"
                                                    viewBox="0 0 20 20"
                                                  >
                                                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                                                  </svg>
                                                  {row.rating}
                                                </span>
                                              ) : (
                                                "-"
                                              )}
                                            </TableCell>
                                          </TableRow>
                                        ))}
                                      </TableBody>
                                    </Table>
                                  </div>
                                )}
                              </div>
                            </TableCell>
                          </TableRow>
                        )}
                      </Fragment>
                    );
                  })}
                </TableBody>
              </Table>
            </div>

            {/* ===== SEPARATE EMAIL RESULTS TABLE (below main table) ===== */}
            {jobs.filter((j) => j.status === "completed").map((job) => {
              const results = jobResults[job.job_id] || [];
              const aggregatedEmails = getAllEmailsFromResults(results);
              const companiesWithEmails = results.filter((r) => r.emails && r.emails.length > 0).length;
              const companiesPending = results.filter((r) => r.email_status === "pending").length;
              const companiesFailed = results.filter((r) => r.email_status === "failed").length;
              const companiesNotStarted = results.filter((r) => !r.email_status || r.email_status === "not_started").length;

              return (
                <div key={job.job_id} className="border-t border-border/40 pt-3">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-xs font-medium text-muted-foreground">
                      📧 Email Results
                    </h3>
                    <div className="flex items-center gap-2">
                      {aggregatedEmails.length > 0 && (
                        <Badge variant="secondary" className="bg-emerald-500/10 text-emerald-600 text-xs border-emerald-500/20 h-5 px-2">
                          {aggregatedEmails.length} emails found
                        </Badge>
                      )}
                      {companiesPending > 0 && (
                        <Badge variant="secondary" className="bg-blue-500/10 text-blue-600 animate-pulse text-xs border-blue-500/20 h-5 px-2">
                          <span className="inline-block w-1 h-1 rounded-full bg-blue-500 mr-1 animate-ping" />
                          {companiesPending} crawling
                        </Badge>
                      )}
                      {companiesFailed > 0 && (
                        <Badge variant="secondary" className="bg-red-500/10 text-red-600 text-xs border-red-500/20 h-5 px-2">
                          {companiesFailed} failed
                        </Badge>
                      )}
                      {companiesNotStarted > 0 && !hasPendingEmailCrawls && (
                        <Badge variant="secondary" className="bg-gray-500/10 text-gray-500 text-xs border-gray-500/20 h-5 px-2">
                          {companiesNotStarted} not started
                        </Badge>
                      )}
                    </div>
                  </div>

                  {/* Status summary */}
                  <div className="flex items-center gap-3 text-[10px] text-muted-foreground mb-2">
                    <span>{companiesWithEmails} companies with emails</span>
                    <span>·</span>
                    <span>{results.length} companies total</span>
                    <span>·</span>
                    <span className="truncate max-w-[200px]" title={job.prompt}>{job.prompt}</span>
                  </div>

                  {aggregatedEmails.length > 0 && (
                    <div>
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-6 text-xs gap-1 text-emerald-600 border-emerald-500/30 hover:bg-emerald-50 dark:hover:bg-emerald-950/20 w-full"
                        type="button"
                        onClick={() => {
                          setEmailsData(aggregatedEmails);
                          setParentJobId(job.job_id);
                          setEmailDialogOpen(true);
                        }}
                      >
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                        </svg>
                        View All {aggregatedEmails.length} Emails
                      </Button>
                      <Dialog open={emailDialogOpen && parentJobId === job.job_id} onOpenChange={(open) => {
                        setEmailDialogOpen(open);
                      }}>
                      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
                        <DialogHeader>
                          <DialogTitle className="flex items-center justify-between">
                            <span className="flex items-center gap-2">
                              <svg className="w-5 h-5 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                              </svg>
                              Email Results
                              <Badge variant="secondary" className="text-xs h-5 bg-emerald-500/10 text-emerald-600 border-emerald-500/20">
                                {emailsData.length} found
                              </Badge>
                            </span>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 text-xs gap-1 hover:bg-muted"
                              onClick={() => {
                                const all = emailsData.map((e: any) => (e.email || "-")).join("\n");
                                navigator.clipboard.writeText(all);
                              }}
                            >
                              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                              </svg>
                              Copy All
                            </Button>
                          </DialogTitle>
                        </DialogHeader>

                        {emailsError && (
                          <div className="flex items-center gap-2 rounded-md border border-red-500/20 bg-red-500/5 px-3 py-3 text-sm text-red-600">
                            <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            {emailsError}
                          </div>
                        )}

                        {!emailsError && emailsData.length === 0 && (
                          <div className="text-center py-10 text-muted-foreground">
                            <svg className="w-10 h-10 mx-auto mb-3 text-muted-foreground/50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                            </svg>
                            <p className="text-sm font-medium">No emails found</p>
                            <p className="text-xs mt-1">
                              No email addresses were found for this crawl.
                            </p>
                          </div>
                        )}

                        {!emailsError && emailsData.length > 0 && (
                          <div className="space-y-2">
                            {emailsData.map((item: any, idx: number) => {
                              const email = item.email || "-";
                              const source = item.company || "-";
                              const sourceUrl = item.url || "";
                              return (
                                <div key={idx} className="flex items-center justify-between rounded-lg border border-border/40 px-3 py-2 hover:bg-muted/50">
                                  <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2">
                                      <a
                                        href={`mailto:${email}`}
                                        className="text-sm font-mono text-blue-500 hover:underline"
                                      >
                                        {email}
                                      </a>
                                      <Button
                                        variant="ghost"
                                        size="sm"
                                        className="h-5 w-5 p-0 hover:bg-muted"
                                        onClick={() => handleCopyEmail(email)}
                                        title="Copy email"
                                      >
                                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                                        </svg>
                                      </Button>
                                    </div>
                                    <p className="text-xs text-muted-foreground mt-0.5 truncate">
                                      Source: {source}
                                      {sourceUrl && (
                                        <a
                                          href={sourceUrl}
                                          target="_blank"
                                          rel="noopener noreferrer"
                                          className="ml-1 text-blue-400 hover:text-blue-500"
                                        >
                                          ↗
                                        </a>
                                      )}
                                    </p>
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </DialogContent>
                    </Dialog>
                  </div>
                  )}
                </div>
              );
            })}
          </>
        )}
      </CardContent>
    </Card>
  );
}