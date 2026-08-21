// TypeScript types for the Google Maps Crawler API

export type OutputFormat = "json" | "csv" | "pretty" | "file" | "print";
export type JobStatus = "pending" | "running" | "completed" | "failed" | "cancelled";

export interface CrawlRequest {
  prompt: string;
  output_format?: OutputFormat;
  headless?: boolean;
  locale?: string;
  max_results?: number;
  track_reviews?: boolean;
  auto_email_crawl?: boolean;
}

export interface EmailCrawlResponse {
  job_id: string;
  parent_job_id: string;
  status: JobStatus;
  created_at: string;
  completed_at?: string;
  emails_found?: number | null;
  error?: string;
}

export interface CrawlResponse {
  job_id: string;
  status: JobStatus;
  prompt: string;
  created_at: string;
  completed_at?: string;
  results_count?: number;
  error?: string;
}

export interface JobResultResponse {
  job_id: string;
  status: JobStatus;
  prompt: string;
  created_at: string;
  completed_at?: string;
  results?: Record<string, any>[];
  error?: string;
  auto_email_crawl?: boolean;
  email_job_status?: string | null;
  emails_found?: number | null;
}

export interface HealthResponse {
  status: string;
  timestamp: string;
  version: string;
}

export interface StatusResponse {
  status: string;
  active_jobs: number;
  queue_length: number;
  total_completed: number;
  total_failed: number;
  timestamp: string;
}

export interface StatsResponse {
  total_crawls: number;
  total_companies_found: number;
  total_pending: number;
  total_running: number;
  total_completed: number;
  total_failed: number;
  total_cancelled: number;
  total_email_crawls?: number;
  total_emails_found?: number;
  timestamp: string;
}

export interface ConfigResponse {
  chrome_profile_path: string;
  page_timeout: number;
  selector_timeout: number;
  scroll_timeout: number;
  max_scroll_attempts: number;
  max_retries: number;
  request_timeout: number;
  viewport_width: number;
  viewport_height: number;
}

export interface BrowserInfoResponse {
  is_initialized: boolean;
  is_running: boolean;
  profile_path: string;
  headless: boolean;
  locale: string;
}

export interface HistoryEntry {
  job_id: string;
  status: JobStatus;
  prompt: string;
  created_at: string;
  completed_at?: string;
  results_count?: number;
  auto_email_crawl?: boolean;
  email_job_status?: string | null;
  emails_found?: number | null;
}

export interface HistoryResponse {
  jobs: HistoryEntry[];
  total: number;
  limit: number;
  offset: number;
}

export type EmailCrawlStatus = "not_started" | "pending" | "completed" | "failed";

export interface CompanyData {
  company_name?: string;
  address?: string;
  phone?: string;
  website?: string;
  category?: string;
  rating?: number;
  reviews?: number;
  opening_hours?: string;
  latitude?: number;
  longitude?: number;
  email?: string;       // comma-separated list (backward compat)
  email_status?: EmailCrawlStatus;
  emails?: string[];    // array of found email addresses
  [key: string]: any;
}

export interface CrawlJob {
  job_id: string;
  status: JobStatus;
  prompt: string;
  created_at: string;
  completed_at?: string;
  results?: CompanyData[];
  error?: string;
}

export interface ReviewData {
  author_name?: string;
  author_image?: string;
  author_local_guide?: boolean;
  author_review_count?: number;
  rating?: number;
  review_text?: string;
  time_relative?: string;
  review_id?: string;
  likes?: number;
  photos?: Array<{ url: string }>;
  owner_response?: string;
  response_time?: string;
  text?: string;        // alias for review_text (backward compat)
  time?: string;         // alias for time_relative (backward compat)
  response_owner?: string; // alias for owner_response (backward compat)
  [key: string]: any;
}

export interface CompanyReviews {
  company_name: string;
  company_index: number;
  job_id: string;
  reviews: ReviewData[];
  total_reviews?: number;
}

// --- Email Sender Types ---

export type SmtpEncryption = "none" | "starttls" | "ssl";

export interface SmtpSettings {
  host: string;
  port: number;
  username: string;
  password: string;
  password_set: boolean;
  encryption: SmtpEncryption;
  from_name: string;
  from_email: string;
  enabled: boolean;
  test_recipient_email: string;
}

export interface SmtpTestResponse {
  success: boolean;
  message: string;
  error?: string;
}

export interface EmailTemplate {
  id: string;
  name: string;
  subject: string;
  body: string;
  html: boolean;
  created_at: string;
  updated_at: string;
}

export interface EmailTemplateCreate {
  name: string;
  subject: string;
  body: string;
  html: boolean;
}

export interface EmailTemplateUpdate {
  name?: string;
  subject?: string;
  body?: string;
  html?: boolean;
}

export interface EmailSendResponse {
  history_id: string;
  job_id: string;
  template_id: string;
  total_recipients: number;
  started_at: string;
}

export interface EmailSendHistoryEntry {
  id: string;
  history_id: string;
  job_id: string;
  email: string;
  company_name: string;
  status: string;
  error?: string;
  sent_at?: string;
}

export interface EmailSendHistoryResponse {
  history: EmailSendHistoryEntry[];
  total: number;
  limit: number;
  offset: number;
}

export interface EmailSendCancelResponse {
  history_id: string;
  cancelled: boolean;
  message: string;
}
