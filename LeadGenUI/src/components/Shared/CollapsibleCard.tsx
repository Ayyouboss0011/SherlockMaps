"use client";

import { useState, type ReactNode } from "react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

interface CollapsibleCardProps {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  defaultOpen?: boolean;
  /** When set, the open/closed state is remembered in localStorage. */
  storageKey?: string;
  /** Extra classes for the content area (e.g. "space-y-4"). */
  contentClassName?: string;
  children: ReactNode;
}

/**
 * A card whose content can be collapsed by clicking the title (chevron).
 * The header keeps its title, description and optional right-side actions;
 * only the card body is toggled.
 */
export default function CollapsibleCard({
  title,
  description,
  actions,
  defaultOpen = true,
  storageKey,
  contentClassName,
  children,
}: CollapsibleCardProps) {
  const [open, setOpen] = useState<boolean>(() => {
    if (storageKey && typeof window !== "undefined") {
      try {
        if (window.localStorage.getItem(storageKey) === "0") return false;
      } catch {
        // Storage unavailable - fall through to default
      }
    }
    return defaultOpen;
  });

  const toggle = () => {
    setOpen((prev) => {
      const next = !prev;
      if (storageKey) {
        try {
          window.localStorage.setItem(storageKey, next ? "1" : "0");
        } catch {
          // ignore
        }
      }
      return next;
    });
  };

  return (
    <Card className="border-border/40">
      <CardHeader>
        <div className="flex items-start justify-between gap-2">
          <button
            type="button"
            onClick={toggle}
            aria-expanded={open}
            className="min-w-0 flex-1 text-left group"
          >
            <div className="flex items-center gap-1.5">
              <svg
                className={`w-4 h-4 flex-shrink-0 text-muted-foreground transition-transform duration-150 ${
                  open ? "" : "-rotate-90"
                }`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
              <span className="text-sm font-medium group-hover:text-foreground/80 transition-colors truncate">
                {title}
              </span>
            </div>
            {description && (
              <p className="text-xs text-muted-foreground mt-1">{description}</p>
            )}
          </button>
          {actions && (
            <div className="flex items-center gap-2 flex-shrink-0">{actions}</div>
          )}
        </div>
      </CardHeader>
      {open && (
        <CardContent className={contentClassName}>{children}</CardContent>
      )}
    </Card>
  );
}
