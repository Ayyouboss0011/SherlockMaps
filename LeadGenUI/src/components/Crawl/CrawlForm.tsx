"use client";

import { useState } from "react";
import { crawlerApi } from "@/lib/api";
import { CrawlResponse } from "@/lib/types";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";

interface CrawlFormProps {
  onCrawlStarted: (response: CrawlResponse) => void;
  onError: (error: string) => void;
}

export default function CrawlForm({ onCrawlStarted, onError }: CrawlFormProps) {
  const [prompt, setPrompt] = useState("");
  const [headless, setHeadless] = useState(false);
  const [trackReviews, setTrackReviews] = useState(true);
  const [autoEmailCrawl, setAutoEmailCrawl] = useState(false);
  const [maxResults, setMaxResults] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) {
      setError("Please enter a search term.");
      return;
    }

    setIsLoading(true);
    setError("");
    setSuccessMessage("");

    try {
      const response = await crawlerApi.startCrawl({
        prompt: prompt.trim(),
        headless,
        track_reviews: trackReviews,
        auto_email_crawl: autoEmailCrawl,
        max_results: maxResults ? parseInt(maxResults, 10) : undefined,
      });
      setSuccessMessage(
        `Crawl started! ID: ${response.job_id.substring(0, 12)}...`
      );
      onCrawlStarted(response);
      setPrompt("");
      setMaxResults("");
      setAutoEmailCrawl(false);

      setTimeout(() => setSuccessMessage(""), 5000);
    } catch (err: any) {
      const msg = err.message || "Crawl could not be started.";
      setError(msg);
      onError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card className="border-border/40">
      <CardContent className="p-4 space-y-4">
        <form onSubmit={handleSubmit} className="space-y-3">
          {/* Prompt */}
          <div className="space-y-1.5">
            <Label htmlFor="prompt" className="text-xs text-muted-foreground">
              Search Term
            </Label>
            <Input
              id="prompt"
              type="text"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="e.g. Restaurants Berlin"
              disabled={isLoading}
              className="h-9 text-sm"
            />
          </div>

          {/* Reviews Toggle - Prominent */}
          <div className="flex items-center justify-between rounded-lg border border-border/40 bg-muted/30 px-4 py-3">
            <div className="space-y-0.5">
              <p className="text-sm font-medium">Review Collection</p>
              <p className="text-xs text-muted-foreground">
                Collects ratings and star ratings of found companies
              </p>
            </div>
            <button
              type="button"
              onClick={() => !isLoading && setTrackReviews(!trackReviews)}
              disabled={isLoading}
              className={`
                relative inline-flex h-[22px] w-[42px] shrink-0 cursor-pointer items-center rounded-full transition-colors
                focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2
                disabled:cursor-not-allowed disabled:opacity-50
                ${trackReviews ? "bg-blue-600" : "bg-gray-300 dark:bg-gray-600"}
              `}
              aria-label="Toggle review collection"
              aria-checked={trackReviews}
              role="switch"
            >
              <span
                className={`
                  pointer-events-none inline-block h-[18px] w-[18px] rounded-full bg-white shadow-md
                  transform transition-transform duration-150 ease-in-out
                  ${trackReviews ? "translate-x-[22px]" : "translate-x-[2px]"}
                `}
              />
            </button>
            <span className={`text-xs font-medium select-none w-6 text-right ${trackReviews ? "text-blue-600" : "text-gray-400"}`}>
              {trackReviews ? "On" : "Off"}
            </span>
          </div>

          {/* Email Crawling Toggle - Prominent */}
          <div className="flex items-center justify-between rounded-lg border border-border/40 bg-muted/30 px-4 py-3">
            <div className="space-y-0.5">
              <p className="text-sm font-medium flex items-center gap-1.5">
                <svg className="w-3.5 h-3.5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
                Email Crawling
              </p>
              <p className="text-xs text-muted-foreground">
                Automatically crawl websites of found companies to extract contact emails
              </p>
            </div>
            <button
              type="button"
              onClick={() => !isLoading && setAutoEmailCrawl(!autoEmailCrawl)}
              disabled={isLoading}
              className={`
                relative inline-flex h-[22px] w-[42px] shrink-0 cursor-pointer items-center rounded-full transition-colors
                focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2
                disabled:cursor-not-allowed disabled:opacity-50
                ${autoEmailCrawl ? "bg-blue-600" : "bg-gray-300 dark:bg-gray-600"}
              `}
              aria-label="Toggle email crawling"
              aria-checked={autoEmailCrawl}
              role="switch"
            >
              <span
                className={`
                  pointer-events-none inline-block h-[18px] w-[18px] rounded-full bg-white shadow-md
                  transform transition-transform duration-150 ease-in-out
                  ${autoEmailCrawl ? "translate-x-[22px]" : "translate-x-[2px]"}
                `}
              />
            </button>
            <span className={`text-xs font-medium select-none w-6 text-right ${autoEmailCrawl ? "text-blue-600" : "text-gray-400"}`}>
              {autoEmailCrawl ? "On" : "Off"}
            </span>
          </div>

          {/* Options Row */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {/* Max Results */}
            <div className="space-y-1.5">
              <Label htmlFor="maxResults" className="text-xs text-muted-foreground">
                Max Results
              </Label>
              <Input
                id="maxResults"
                type="number"
                value={maxResults}
                onChange={(e) => setMaxResults(e.target.value)}
                placeholder="Unlimited"
                min={1}
                disabled={isLoading}
                className="h-9 text-sm"
              />
            </div>

            {/* Headless Toggle */}
            <div className="flex items-center pt-6">
              <Switch
                checked={headless}
                onCheckedChange={setHeadless}
                disabled={isLoading}
              />
            </div>
          </div>

          {/* Info hint when reviews are disabled */}
          {!trackReviews && (
            <div className="flex items-center gap-2 rounded-md border border-blue-500/20 bg-blue-500/5 px-3 py-2 text-xs text-blue-600">
              <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Reviews are disabled - crawl runs faster but no review data will be collected.
            </div>
          )}

          {/* Success Message */}
          {successMessage && (
            <div className="flex items-center gap-2 rounded-md border border-emerald-500/20 bg-emerald-500/5 px-3 py-2 text-xs text-emerald-600">
              <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {successMessage}
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="flex items-center gap-2 rounded-md border border-red-500/20 bg-red-500/5 px-3 py-2 text-xs text-red-600">
              <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {error}
            </div>
          )}

          {/* Submit Button */}
          <div className="flex justify-end pt-1">
            <Button
              type="submit"
              disabled={isLoading || !prompt.trim()}
              className="h-8 text-xs gap-1.5"
            >
              {isLoading ? (
                <>
                  <span className="inline-block w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin" />
                  Starting...
                </>
              ) : (
                <>
                  <svg
                    className="w-3.5 h-3.5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M13 10V3L4 14h7v7l9-11h-7z"
                    />
                  </svg>
                  Start Crawl
                </>
              )}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}