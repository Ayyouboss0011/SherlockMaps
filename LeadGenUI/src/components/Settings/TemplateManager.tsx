"use client";

import { useState, useEffect, useCallback } from "react";
import { crawlerApi } from "@/lib/api";
import { EmailTemplate } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";

const PLACEHOLDERS = [
  "{{company_name}}",
  "{{company_website}}",
  "{{company_address}}",
  "{{sender_name}}",
  "{{sender_email}}",
];

interface TemplateForm {
  id?: string;
  name: string;
  subject: string;
  body: string;
  html: boolean;
}

const EMPTY_FORM: TemplateForm = { name: "", subject: "", body: "", html: false };

export default function TemplateManager() {
  const [templates, setTemplates] = useState<EmailTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState<TemplateForm>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await crawlerApi.getTemplates();
      setTemplates(data);
    } catch (err: any) {
      setError(err.message || "Could not load templates.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const openCreate = () => {
    setForm(EMPTY_FORM);
    setError(null);
    setDialogOpen(true);
  };

  const openEdit = (template: EmailTemplate) => {
    setForm({
      id: template.id,
      name: template.name,
      subject: template.subject,
      body: template.body,
      html: template.html,
    });
    setError(null);
    setDialogOpen(true);
  };

  const handleSave = async () => {
    if (!form.name.trim() || !form.subject.trim() || !form.body.trim()) {
      setError("Template name, subject and body are required.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const payload = {
        name: form.name.trim(),
        subject: form.subject.trim(),
        body: form.body,
        html: form.html,
      };
      if (form.id) {
        await crawlerApi.updateTemplate(form.id, payload);
      } else {
        await crawlerApi.createTemplate(payload);
      }
      setDialogOpen(false);
      await load();
    } catch (err: any) {
      setError(err.message || "Could not save template.");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (template: EmailTemplate) => {
    if (!window.confirm(`Delete template "${template.name}"?`)) return;
    try {
      await crawlerApi.deleteTemplate(template.id);
      await load();
    } catch (err: any) {
      setError(err.message || "Could not delete template.");
    }
  };

  const insertPlaceholder = (placeholder: string) => {
    setForm((prev) => ({ ...prev, body: prev.body + placeholder }));
  };

  return (
    <Card className="border-border/40">
      <CardHeader>
        <div className="flex items-center justify-between gap-2">
          <div>
            <CardTitle className="text-sm font-medium">Email Templates</CardTitle>
            <CardDescription className="text-xs">
              Templates used when sending emails to crawled contacts.
            </CardDescription>
          </div>
          <Button type="button" onClick={openCreate} className="h-8 text-xs gap-1.5">
            New Template
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {error && (
          <div className="flex items-center gap-2 rounded-md border border-red-500/20 bg-red-500/5 px-3 py-2 text-xs text-red-600">
            {error}
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-6">
            <div className="inline-block w-4 h-4 border-2 border-foreground border-t-transparent rounded-full animate-spin" />
            <span className="ml-2 text-xs text-muted-foreground">Loading templates...</span>
          </div>
        ) : templates.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <p className="text-xs">No templates yet.</p>
            <p className="text-xs mt-1">Create a template to start sending emails.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {templates.map((template) => (
              <div
                key={template.id}
                className="flex items-start justify-between gap-3 rounded-lg border border-border/40 px-3 py-2.5 hover:bg-muted/40"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium truncate">{template.name}</p>
                    {template.html && (
                      <Badge variant="secondary" className="text-[10px] h-4 px-1.5">
                        HTML
                      </Badge>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground mt-0.5 truncate">
                    {template.subject}
                  </p>
                  <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">
                    {template.body}
                  </p>
                </div>
                <div className="flex items-center gap-1 flex-shrink-0">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 px-2 text-xs"
                    onClick={() => openEdit(template)}
                  >
                    Edit
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 px-2 text-xs text-red-600 hover:text-red-700"
                    onClick={() => handleDelete(template)}
                  >
                    Delete
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}

        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>{form.id ? "Edit Template" : "New Template"}</DialogTitle>
              <DialogDescription>
                Use placeholders to personalize each email.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-3">
              <div className="space-y-1.5">
                <Label htmlFor="tmpl-name" className="text-xs text-muted-foreground">
                  Template Name
                </Label>
                <Input
                  id="tmpl-name"
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
                  placeholder="Follow-up message"
                  className="h-9 text-sm"
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="tmpl-subject" className="text-xs text-muted-foreground">
                  Subject
                </Label>
                <Input
                  id="tmpl-subject"
                  type="text"
                  value={form.subject}
                  onChange={(e) => setForm((prev) => ({ ...prev, subject: e.target.value }))}
                  placeholder="Hello {{company_name}}"
                  className="h-9 text-sm"
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="tmpl-body" className="text-xs text-muted-foreground">
                  Body
                </Label>
                <Textarea
                  id="tmpl-body"
                  value={form.body}
                  onChange={(e) => setForm((prev) => ({ ...prev, body: e.target.value }))}
                  placeholder="Dear {{company_name}},\n\nwe would like to offer our services..."
                  rows={8}
                  className="text-sm"
                />
                <div className="flex items-center flex-wrap gap-1 pt-1">
                  <span className="text-[10px] text-muted-foreground mr-1">Insert:</span>
                  {PLACEHOLDERS.map((p) => (
                    <button
                      key={p}
                      type="button"
                      onClick={() => insertPlaceholder(p)}
                      className="rounded border border-border/50 bg-muted/50 px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground hover:bg-muted hover:text-foreground"
                    >
                      {p}
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex items-center justify-between rounded-lg border border-border/40 bg-muted/30 px-4 py-2.5">
                <div className="space-y-0.5">
                  <p className="text-sm font-medium">HTML Format</p>
                  <p className="text-xs text-muted-foreground">Send the body as HTML</p>
                </div>
                <button
                  type="button"
                  onClick={() => setForm((prev) => ({ ...prev, html: !prev.html }))}
                  className={`
                    relative inline-flex h-[22px] w-[42px] shrink-0 cursor-pointer items-center rounded-full transition-colors
                    focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2
                    ${form.html ? "bg-blue-600" : "bg-gray-300 dark:bg-gray-600"}
                  `}
                  aria-label="Toggle HTML format"
                  aria-checked={form.html}
                  role="switch"
                >
                  <span
                    className={`
                      pointer-events-none inline-block h-[18px] w-[18px] rounded-full bg-white shadow-md
                      transform transition-transform duration-150 ease-in-out
                      ${form.html ? "translate-x-[22px]" : "translate-x-[2px]"}
                    `}
                  />
                </button>
                <span className={`text-xs font-medium select-none w-6 text-right ${form.html ? "text-blue-600" : "text-gray-400"}`}>
                  {form.html ? "On" : "Off"}
                </span>
              </div>

              {error && (
                <div className="flex items-center gap-2 rounded-md border border-red-500/20 bg-red-500/5 px-3 py-2 text-xs text-red-600">
                  {error}
                </div>
              )}
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setDialogOpen(false)} className="h-8 text-xs">
                Cancel
              </Button>
              <Button onClick={handleSave} disabled={saving} className="h-8 text-xs gap-1.5">
                {saving ? "Saving..." : "Save Template"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  );
}
