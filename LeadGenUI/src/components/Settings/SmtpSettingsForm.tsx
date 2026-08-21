"use client";

import { useEffect, useState, useCallback } from "react";
import { crawlerApi } from "@/lib/api";
import { SmtpSettings, SmtpEncryption } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";

const ENCRYPTION_OPTIONS: { value: SmtpEncryption; label: string }[] = [
  { value: "starttls", label: "STARTTLS" },
  { value: "ssl", label: "SSL / TLS" },
  { value: "none", label: "None" },
];

export default function SmtpSettingsForm() {
  const [settings, setSettings] = useState<SmtpSettings>({
    host: "",
    port: 587,
    username: "",
    password: "",
    password_set: false,
    encryption: "starttls",
    from_name: "",
    from_email: "",
    enabled: false,
    test_recipient_email: "",
  });
  const [passwordDirty, setPasswordDirty] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Test connection
  const [testEmail, setTestEmail] = useState("");
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await crawlerApi.getSmtpSettings();
      setSettings(data);
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Could not load SMTP settings." });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const set = <K extends keyof SmtpSettings>(key: K, value: SmtpSettings[K]) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = async () => {
    setSaving(true);
    setMessage(null);
    try {
      const payload: Record<string, any> = {
        host: settings.host,
        port: settings.port,
        username: settings.username,
        encryption: settings.encryption,
        from_name: settings.from_name,
        from_email: settings.from_email,
        enabled: settings.enabled,
        test_recipient_email: settings.test_recipient_email,
      };
      if (passwordDirty) {
        payload.password = settings.password;
      }
      const saved = await crawlerApi.updateSmtpSettings(payload);
      setSettings(saved);
      setPasswordDirty(false);
      setMessage({ type: "success", text: "SMTP settings saved." });
      setTimeout(() => setMessage(null), 4000);
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Could not save SMTP settings." });
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    if (!testEmail.trim()) return;
    setTesting(true);
    setTestResult(null);
    try {
      const result = await crawlerApi.testSmtp(testEmail.trim());
      setTestResult({
        type: result.success ? "success" : "error",
        text: result.success ? result.message : result.error || result.message,
      });
    } catch (err: any) {
      setTestResult({ type: "error", text: err.message || "Test failed." });
    } finally {
      setTesting(false);
    }
  };

  if (loading) {
    return (
      <Card className="border-border/40">
        <CardContent className="p-4">
          <div className="flex items-center justify-center py-6">
            <div className="inline-block w-4 h-4 border-2 border-foreground border-t-transparent rounded-full animate-spin" />
            <span className="ml-2 text-xs text-muted-foreground">Loading SMTP settings...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-border/40">
      <CardHeader>
        <CardTitle className="text-sm font-medium">SMTP Settings</CardTitle>
        <CardDescription className="text-xs">
          Configure the SMTP server used to send emails to crawled contacts.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="space-y-1.5">
            <Label htmlFor="smtp-host" className="text-xs text-muted-foreground">
              SMTP Host
            </Label>
            <Input
              id="smtp-host"
              type="text"
              value={settings.host}
              onChange={(e) => set("host", e.target.value)}
              placeholder="smtp.example.com"
              className="h-9 text-sm"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="smtp-port" className="text-xs text-muted-foreground">
              Port
            </Label>
            <Input
              id="smtp-port"
              type="number"
              value={settings.port}
              onChange={(e) => set("port", parseInt(e.target.value, 10) || 0)}
              placeholder="587"
              className="h-9 text-sm"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="smtp-encryption" className="text-xs text-muted-foreground">
              Encryption
            </Label>
            <select
              id="smtp-encryption"
              value={settings.encryption}
              onChange={(e) => set("encryption", e.target.value as SmtpEncryption)}
              className="h-9 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm transition-colors outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30"
            >
              {ENCRYPTION_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value} className="bg-background">
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <Label htmlFor="smtp-username" className="text-xs text-muted-foreground">
              Username
            </Label>
            <Input
              id="smtp-username"
              type="text"
              value={settings.username}
              onChange={(e) => set("username", e.target.value)}
              placeholder="user@example.com"
              className="h-9 text-sm"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="smtp-password" className="text-xs text-muted-foreground">
              Password
            </Label>
            <Input
              id="smtp-password"
              type="password"
              value={settings.password}
              onChange={(e) => {
                set("password", e.target.value);
                setPasswordDirty(true);
              }}
              placeholder={settings.password_set && !passwordDirty ? "•••••••• (unchanged)" : ""}
              className="h-9 text-sm"
            />
            {settings.password_set && (
              <p className="text-[10px] text-muted-foreground">
                A password is stored. Leave empty to keep it.
              </p>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <Label htmlFor="smtp-from-name" className="text-xs text-muted-foreground">
              Sender Name
            </Label>
            <Input
              id="smtp-from-name"
              type="text"
              value={settings.from_name}
              onChange={(e) => set("from_name", e.target.value)}
              placeholder="SherlockMaps"
              className="h-9 text-sm"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="smtp-from-email" className="text-xs text-muted-foreground">
              Sender Email
            </Label>
            <Input
              id="smtp-from-email"
              type="email"
              value={settings.from_email}
              onChange={(e) => set("from_email", e.target.value)}
              placeholder="crawler@example.com"
              className="h-9 text-sm"
            />
          </div>
        </div>

        {/* Enabled toggle */}
        <div className="flex items-center justify-between rounded-lg border border-border/40 bg-muted/30 px-4 py-3">
          <div className="space-y-0.5">
            <p className="text-sm font-medium">Enable Sending</p>
            <p className="text-xs text-muted-foreground">
              Allow the crawler to send emails through this SMTP server
            </p>
          </div>
          <button
            type="button"
            onClick={() => set("enabled", !settings.enabled)}
            className={`
              relative inline-flex h-[22px] w-[42px] shrink-0 cursor-pointer items-center rounded-full transition-colors
              focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2
              ${settings.enabled ? "bg-blue-600" : "bg-gray-300 dark:bg-gray-600"}
            `}
            aria-label="Toggle email sending"
            aria-checked={settings.enabled}
            role="switch"
          >
            <span
              className={`
                pointer-events-none inline-block h-[18px] w-[18px] rounded-full bg-white shadow-md
                transform transition-transform duration-150 ease-in-out
                ${settings.enabled ? "translate-x-[22px]" : "translate-x-[2px]"}
              `}
            />
          </button>
          <span className={`text-xs font-medium select-none w-6 text-right ${settings.enabled ? "text-blue-600" : "text-gray-400"}`}>
            {settings.enabled ? "On" : "Off"}
          </span>
        </div>

        {/* Test recipient email */}
        <div className="space-y-1.5">
          <Label htmlFor="smtp-test-recipient" className="text-xs text-muted-foreground">
            Test Recipient Email
          </Label>
          <Input
            id="smtp-test-recipient"
            type="email"
            value={settings.test_recipient_email}
            onChange={(e) => set("test_recipient_email", e.target.value)}
            placeholder="test@example.com"
            className="h-9 text-sm"
          />
          <p className="text-[10px] text-muted-foreground">
            Test runs send every personalized email to this address instead of the real recipients.
          </p>
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

        <div className="flex items-center gap-2">
          <Button type="button" onClick={handleSave} disabled={saving} className="h-8 text-xs gap-1.5">
            {saving ? (
              <>
                <span className="inline-block w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin" />
                Saving...
              </>
            ) : (
              "Save Settings"
            )}
          </Button>
        </div>

        {/* Test connection */}
        <div className="border-t border-border/40 pt-4 space-y-3">
          <div>
            <p className="text-sm font-medium">Test Connection</p>
            <p className="text-xs text-muted-foreground">
              Send a test email to verify the SMTP configuration.
            </p>
          </div>
          <div className="flex flex-col sm:flex-row gap-2">
            <Input
              type="email"
              value={testEmail}
              onChange={(e) => setTestEmail(e.target.value)}
              placeholder="test@example.com"
              className="h-8 text-sm sm:max-w-xs"
            />
            <Button
              type="button"
              variant="outline"
              onClick={handleTest}
              disabled={testing || !testEmail.trim()}
              className="h-8 text-xs gap-1.5"
            >
              {testing ? "Testing..." : "Send Test Email"}
            </Button>
          </div>
          {testResult && (
            <div className={`flex items-center gap-2 rounded-md border px-3 py-2 text-xs ${
              testResult.type === "success"
                ? "border-emerald-500/20 bg-emerald-500/5 text-emerald-600"
                : "border-red-500/20 bg-red-500/5 text-red-600"
            }`}>
              {testResult.text}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
