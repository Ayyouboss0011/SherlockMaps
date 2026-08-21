"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard" },
  { href: "/send-email", label: "Send Emails" },
  { href: "/settings", label: "Settings" },
];

interface HeaderNavProps {
  crawlerOnline?: boolean;
  stats?: { total_crawls?: number } | null;
}

export default function HeaderNav({ crawlerOnline, stats }: HeaderNavProps) {
  const pathname = usePathname();

  return (
    <header className="border-b border-border/50 sticky top-0 bg-background/95 backdrop-blur-sm z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-12 gap-4">
          <div className="flex items-center gap-2.5">
            <Link href="/" className="flex items-center gap-2.5">
              <img
                src="/SherlockMaps.png"
                alt="SherlockMaps"
                className="w-10 h-10 object-contain"
              />
              <div>
                <h1 className="text-sm font-medium text-foreground leading-none">
                  SherlockMaps
                </h1>
              </div>
            </Link>

            {/* Navigation */}
            <nav className="ml-6 flex items-center gap-1">
              {NAV_ITEMS.map((item) => {
                const active =
                  item.href === "/"
                    ? pathname === "/"
                    : pathname.startsWith(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "px-3 py-1.5 rounded-md text-xs font-medium transition-colors",
                      active
                        ? "bg-muted text-foreground"
                        : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                    )}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </div>

          {/* Crawler Status */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <div
                className={cn(
                  "w-1.5 h-1.5 rounded-full",
                  crawlerOnline ? "bg-emerald-500" : "bg-red-500"
                )}
              />
              <span className="text-xs text-muted-foreground">
                {crawlerOnline ? "Online" : "Offline"}
              </span>
            </div>
            {stats && (
              <Badge variant="secondary" className="text-xs h-5 px-1.5">
                {stats.total_crawls} Crawls
              </Badge>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
