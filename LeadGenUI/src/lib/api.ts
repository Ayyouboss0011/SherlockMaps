import {
  CrawlRequest,
  CrawlResponse,
  JobResultResponse,
  StatusResponse,
  StatsResponse,
  HistoryResponse,
  ConfigResponse,
  BrowserInfoResponse,
  CompanyData,
  ReviewData,
  CompanyReviews,
  EmailCrawlResponse,
  SmtpSettings,
  SmtpTestResponse,
  EmailTemplate,
  EmailTemplateCreate,
  EmailTemplateUpdate,
  EmailSendResponse,
  EmailSendHistoryResponse,
  EmailSendCancelResponse,
} from "./types";

const DEFAULT_API_URL = "http://localhost:8000";

function getApiUrl(): string {
  if (typeof window !== "undefined") {
    return (process.env.NEXT_PUBLIC_CRAWLER_API_URL as string) || DEFAULT_API_URL;
  }
  return process.env.CRAWLER_API_URL || DEFAULT_API_URL;
}

async function apiFetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const baseUrl = getApiUrl();
  const url = `${baseUrl}${endpoint}`;

  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
    },
    ...options,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`API Error (${response.status}): ${errorText}`);
  }

  const data = await response.json();
  return data as T;
}

// Crawler API client
export const crawlerApi = {
  // Health check
  async health(): Promise<{ status: string; timestamp: string }> {
    return apiFetch("/health");
  },

  // Status
  async getStatus(): Promise<StatusResponse> {
    return apiFetch<StatusResponse>("/status");
  },

  // Stats
  async getStats(): Promise<StatsResponse> {
    return apiFetch<StatsResponse>("/stats");
  },

  // Start a new crawl
  async startCrawl(request: CrawlRequest): Promise<CrawlResponse> {
    return apiFetch<CrawlResponse>("/crawl", {
      method: "POST",
      body: JSON.stringify(request),
    });
  },

  // Get job status
  async getJobStatus(jobId: string): Promise<JobResultResponse> {
    return apiFetch<JobResultResponse>(`/crawl/${jobId}`);
  },

  // Get job results
  async getJobResults(jobId: string): Promise<JobResultResponse> {
    return apiFetch<JobResultResponse>(`/crawl/${jobId}/results`);
  },

  // Cancel a job
  async cancelJob(jobId: string): Promise<{ message: string; job_id: string; status: string }> {
    return apiFetch(`/crawl/${jobId}`, {
      method: "DELETE",
    });
  },

  // Get crawl history
  async getCrawlHistory(limit: number = 50, offset: number = 0): Promise<HistoryResponse> {
    return apiFetch<HistoryResponse>(`/crawl/history?limit=${limit}&offset=${offset}`);
  },

  // Get all results
  async getAllResults(format: string = "json"): Promise<CompanyData[]> {
    const response = await fetch(`${getApiUrl()}/results?format=${format}`);
    if (!response.ok) {
      return [];
    }
    const data = await response.json();
    return Array.isArray(data) ? data : [];
  },

  // Export results
  async exportResults(format: string = "json"): Promise<Blob> {
    const response = await fetch(`${getApiUrl()}/results?format=${format}`);
    if (!response.ok) {
      throw new Error(`Export failed with status ${response.status}`);
    }
    return response.blob();
  },

  // Clear results
  async clearResults(): Promise<{ message: string; cleared_count: number }> {
    return apiFetch("/results/clear", {
      method: "DELETE",
    });
  },

  // Get config
  async getConfig(): Promise<ConfigResponse> {
    return apiFetch<ConfigResponse>("/config");
  },

  // Get browser info
  async getBrowserInfo(): Promise<BrowserInfoResponse> {
    return apiFetch<BrowserInfoResponse>("/browser/info");
  },

  // Review endpoints
  async getAllReviews(limit: number = 20, offset: number = 0): Promise<{ reviews: ReviewData[]; total: number }> {
    return apiFetch<Promise<{ reviews: ReviewData[]; total: number }>>(`/reviews?limit=${limit}&offset=${offset}`);
  },

  async getReviewsByJob(jobId: string): Promise<CompanyReviews[]> {
    return apiFetch<CompanyReviews[]>(`/reviews/job/${jobId}`);
  },

  async getReviewsByCompany(jobId: string, companyIndex: number): Promise<{ company_name: string; reviews: ReviewData[]; total: number }> {
    return apiFetch<Promise<{ company_name: string; reviews: ReviewData[]; total: number }>>(`/reviews/company/${jobId}/${companyIndex}`);
  },

  // Email crawling endpoints
  async startEmailCrawl(jobId: string): Promise<EmailCrawlResponse> {
    return apiFetch<EmailCrawlResponse>("/email-crawl", {
      method: "POST",
      body: JSON.stringify({ job_id: jobId }),
    });
  },

  async getEmailJobByParent(parentJobId: string): Promise<EmailCrawlResponse | null> {
    try {
      return await apiFetch<EmailCrawlResponse | null>(`/email-crawl/parent/${parentJobId}`);
    } catch {
      return null;
    }
  },

  // SMTP settings
  async getSmtpSettings(): Promise<SmtpSettings> {
    return apiFetch<SmtpSettings>("/smtp/settings");
  },

  async updateSmtpSettings(settings: Partial<SmtpSettings>): Promise<SmtpSettings> {
    return apiFetch<SmtpSettings>("/smtp/settings", {
      method: "PUT",
      body: JSON.stringify(settings),
    });
  },

  async testSmtp(toEmail: string): Promise<SmtpTestResponse> {
    return apiFetch<SmtpTestResponse>("/smtp/test", {
      method: "POST",
      body: JSON.stringify({ to_email: toEmail }),
    });
  },

  // Templates
  async getTemplates(): Promise<EmailTemplate[]> {
    return apiFetch<EmailTemplate[]>("/templates");
  },

  async createTemplate(data: EmailTemplateCreate): Promise<EmailTemplate> {
    return apiFetch<EmailTemplate>("/templates", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async updateTemplate(templateId: string, data: EmailTemplateUpdate): Promise<EmailTemplate> {
    return apiFetch<EmailTemplate>(`/templates/${templateId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  async deleteTemplate(templateId: string): Promise<{ message: string; cleared_count: number }> {
    return apiFetch(`/templates/${templateId}`, {
      method: "DELETE",
    });
  },

  // Send emails
  async getJobRecipients(jobId: string): Promise<{ email: string; company_name: string; company_website: string; company_address: string }[]> {
    return apiFetch<{ email: string; company_name: string; company_website: string; company_address: string }[]>(`/emails/recipients/${jobId}`);
  },

  async sendEmails(jobId: string, templateId: string, delaySeconds: number = 2, test: boolean = false): Promise<EmailSendResponse> {
    return apiFetch<EmailSendResponse>("/emails/send", {
      method: "POST",
      body: JSON.stringify({ job_id: jobId, template_id: templateId, delay_seconds: delaySeconds, test }),
    });
  },

  async getSendHistory(limit: number = 100, offset: number = 0): Promise<EmailSendHistoryResponse> {
    return apiFetch<EmailSendHistoryResponse>(`/emails/send/history?limit=${limit}&offset=${offset}`);
  },

  async cancelEmailSend(historyId: string): Promise<EmailSendCancelResponse> {
    return apiFetch<EmailSendCancelResponse>(`/emails/send/${historyId}/cancel`, {
      method: "POST",
    });
  },

  async clearSendHistory(): Promise<{ message: string; cleared_count: number }> {
    return apiFetch("/emails/send/history", {
      method: "DELETE",
    });
  },
};
