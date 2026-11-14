#!/usr/bin/env python3
"""Capture deterministic README screenshots for the Sherlock Maps UI.

The script talks to a locally running Next.js build and fulfils every ``/api``
request with fixture data. No crawler, Google Maps request, SMTP server or
browser profile is required:

    npm run build
    npm start
    python scripts/capture_screenshots.py

The screenshots are written to ``docs/assets/screenshots``.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "docs" / "assets" / "screenshots"

NOW = datetime.now(timezone.utc).replace(microsecond=0)
HISTORY = [
    {
        "job_id": "8f3c1a2e-0b7d-4a8f-9d2e-1c6b5a4f3e21",
        "status": "completed",
        "prompt": "Restaurants Berlin",
        "created_at": (NOW - timedelta(minutes=18)).isoformat(),
        "completed_at": (NOW - timedelta(minutes=14)).isoformat(),
        "results_count": 42,
        "auto_email_crawl": True,
        "email_job_status": "completed",
        "emails_found": 18,
    },
    {
        "job_id": "2b9d4c7a-6e1f-4c3a-8b5d-0a9e7f6c5d42",
        "status": "completed",
        "prompt": "Dentists Munich",
        "created_at": (NOW - timedelta(hours=2, minutes=6)).isoformat(),
        "completed_at": (NOW - timedelta(hours=1, minutes=52)).isoformat(),
        "results_count": 27,
        "auto_email_crawl": True,
        "email_job_status": "completed",
        "emails_found": 11,
    },
    {
        "job_id": "6d1e8f4b-3a2c-4d9e-b7f0-5c8a1e2d3b64",
        "status": "completed",
        "prompt": "Cafés Hamburg",
        "created_at": (NOW - timedelta(hours=4, minutes=25)).isoformat(),
        "completed_at": (NOW - timedelta(hours=4, minutes=2)).isoformat(),
        "results_count": 31,
        "auto_email_crawl": True,
        "email_job_status": "completed",
        "emails_found": 14,
    },
    {
        "job_id": "a4c7f2d9-5b3e-4a1c-9f8d-7e6b5a4c3d21",
        "status": "failed",
        "prompt": "Gyms Vienna",
        "created_at": (NOW - timedelta(hours=6, minutes=11)).isoformat(),
        "completed_at": (NOW - timedelta(hours=6, minutes=9)).isoformat(),
        "results_count": 0,
        "auto_email_crawl": False,
        "email_job_status": None,
        "emails_found": None,
    },
]

COMPANIES = [
    {
        "name": "Café Morgenrot",
        "company_name": "Café Morgenrot",
        "address": "Torstraße 12, 10119 Berlin",
        "phone": "+49 30 1234 5678",
        "website": "https://cafemorgenrot.example",
        "category": "Café",
        "rating": 4.8,
        "reviews": 214,
        "email_status": "completed",
        "emails": ["hello@cafemorgenrot.example"],
    },
    {
        "name": "Trattoria Bellavista",
        "company_name": "Trattoria Bellavista",
        "address": "Kastanienallee 44, 10435 Berlin",
        "phone": "+49 30 2345 6789",
        "website": "https://bellavista.example",
        "category": "Italian restaurant",
        "rating": 4.7,
        "reviews": 389,
        "email_status": "completed",
        "emails": ["info@bellavista.example"],
    },
    {
        "name": "Nordic Roast",
        "company_name": "Nordic Roast",
        "address": "Oranienstraße 7, 10999 Berlin",
        "phone": "+49 30 3456 7890",
        "website": "https://nordicroast.example",
        "category": "Coffee shop",
        "rating": 4.9,
        "reviews": 512,
        "email_status": "completed",
        "emails": ["hello@nordicroast.example"],
    },
    {
        "name": "Bistro Lumen",
        "company_name": "Bistro Lumen",
        "address": "Prenzlauer Allee 88, 10405 Berlin",
        "phone": "+49 30 4567 8901",
        "website": "https://bistrolumen.example",
        "category": "Bistro",
        "rating": 4.6,
        "reviews": 176,
        "email_status": "completed",
        "emails": ["contact@bistrolumen.example"],
    },
    {
        "name": "Sushi Kaito",
        "company_name": "Sushi Kaito",
        "address": "Rosenthaler Straße 51, 10178 Berlin",
        "phone": "+49 30 5678 9012",
        "website": "https://sushikaito.example",
        "category": "Sushi restaurant",
        "rating": 4.8,
        "reviews": 263,
        "email_status": "completed",
        "emails": ["team@sushikaito.example"],
    },
    {
        "name": "Green Bowl",
        "company_name": "Green Bowl",
        "address": "Warschauer Straße 33, 10243 Berlin",
        "phone": "+49 30 6789 0123",
        "website": "https://greenbowl.example",
        "category": "Vegan restaurant",
        "rating": 4.5,
        "reviews": 198,
        "email_status": "completed",
        "emails": ["hi@greenbowl.example"],
    },
    {
        "name": "Bäckerei Kranz",
        "company_name": "Bäckerei Kranz",
        "address": "Bergmannstraße 21, 10961 Berlin",
        "phone": "+49 30 7890 1234",
        "website": "https://baeckerei-kranz.example",
        "category": "Bakery",
        "rating": 4.7,
        "reviews": 144,
        "email_status": "completed",
        "emails": ["info@baeckerei-kranz.example"],
    },
    {
        "name": "Pasta & Passione",
        "company_name": "Pasta & Passione",
        "address": "Kollwitzstraße 60, 10435 Berlin",
        "phone": "+49 30 8901 2345",
        "website": "https://pasta-passione.example",
        "category": "Italian restaurant",
        "rating": 4.6,
        "reviews": 231,
        "email_status": "completed",
        "emails": ["hello@pasta-passione.example"],
    },
    {
        "name": "The Daily Grind",
        "company_name": "The Daily Grind",
        "address": "Neue Schönhauser Straße 14, 10178 Berlin",
        "phone": "+49 30 9012 3456",
        "website": "https://thedailygrind.example",
        "category": "Coffee shop",
        "rating": 4.8,
        "reviews": 307,
        "email_status": "completed",
        "emails": ["hey@thedailygrind.example"],
    },
    {
        "name": "Mauerpark Kitchen",
        "company_name": "Mauerpark Kitchen",
        "address": "Eberswalder Straße 19, 10437 Berlin",
        "phone": "+49 30 0123 4567",
        "website": "https://mauerpark-kitchen.example",
        "category": "Restaurant",
        "rating": 4.4,
        "reviews": 121,
        "email_status": "completed",
        "emails": ["hello@mauerpark-kitchen.example"],
    },
]

TEMPLATES = [
    {
        "id": "tpl-local-seo",
        "name": "Local SEO Audit",
        "subject": "A quick idea for {{company_name}}",
        "body": (
            "Hi {{company_name}} team,\n\n"
            "I had a look at {{company_website}} and noticed a few quick wins for "
            "your local search visibility.\n\n"
            "Would you be open to a short call this week?\n\n"
            "Best,\n{{sender_name}}"
        ),
        "html": False,
        "created_at": (NOW - timedelta(days=12)).isoformat(),
        "updated_at": (NOW - timedelta(days=2)).isoformat(),
    },
    {
        "id": "tpl-website-review",
        "name": "Website Review",
        "subject": "Feedback on {{company_website}}",
        "body": (
            "Hi {{company_name}} team,\n\n"
            "I reviewed your website and recorded three practical improvements "
            "for mobile visitors.\n\n"
            "Want me to send the short video?\n\n"
            "Cheers,\n{{sender_name}}"
        ),
        "html": False,
        "created_at": (NOW - timedelta(days=8)).isoformat(),
        "updated_at": (NOW - timedelta(days=1)).isoformat(),
    },
    {
        "id": "tpl-intro",
        "name": "Friendly Intro",
        "subject": "Hello from {{sender_name}}",
        "body": "Hi {{company_name}} team,\n\nA short, friendly introduction...",
        "html": False,
        "created_at": (NOW - timedelta(days=4)).isoformat(),
        "updated_at": (NOW - timedelta(days=4)).isoformat(),
    },
]

RECIPIENTS = [
    {"email": "hello@cafemorgenrot.example", "company_name": "Café Morgenrot", "company_website": "https://cafemorgenrot.example", "company_address": "Torstraße 12, 10119 Berlin"},
    {"email": "info@bellavista.example", "company_name": "Trattoria Bellavista", "company_website": "https://bellavista.example", "company_address": "Kastanienallee 44, 10435 Berlin"},
    {"email": "hello@nordicroast.example", "company_name": "Nordic Roast", "company_website": "https://nordicroast.example", "company_address": "Oranienstraße 7, 10999 Berlin"},
    {"email": "contact@bistrolumen.example", "company_name": "Bistro Lumen", "company_website": "https://bistrolumen.example", "company_address": "Prenzlauer Allee 88, 10405 Berlin"},
    {"email": "team@sushikaito.example", "company_name": "Sushi Kaito", "company_website": "https://sushikaito.example", "company_address": "Rosenthaler Straße 51, 10178 Berlin"},
    {"email": "hi@greenbowl.example", "company_name": "Green Bowl", "company_website": "https://greenbowl.example", "company_address": "Warschauer Straße 33, 10243 Berlin"},
    {"email": "info@baeckerei-kranz.example", "company_name": "Bäckerei Kranz", "company_website": "https://baeckerei-kranz.example", "company_address": "Bergmannstraße 21, 10961 Berlin"},
    {"email": "hello@pasta-passione.example", "company_name": "Pasta & Passione", "company_website": "https://pasta-passione.example", "company_address": "Kollwitzstraße 60, 10435 Berlin"},
]

BLACKLIST = [
    {"email": "press@example.com", "added_at": (NOW - timedelta(days=9)).isoformat(), "note": "Asked not to be contacted"},
    {"email": "privacy@example.com", "added_at": (NOW - timedelta(days=4)).isoformat(), "note": "Privacy request"},
]

SEND_HISTORY = [
    {
        "id": "send-1",
        "history_id": "send-1",
        "job_id": HISTORY[0]["job_id"],
        "email": "hello@cafemorgenrot.example",
        "company_name": "Café Morgenrot",
        "status": "sent",
        "sent_at": (NOW - timedelta(minutes=9)).isoformat(),
    },
    {
        "id": "send-2",
        "history_id": "send-2",
        "job_id": HISTORY[0]["job_id"],
        "email": "info@bellavista.example",
        "company_name": "Trattoria Bellavista",
        "status": "sent",
        "sent_at": (NOW - timedelta(minutes=8)).isoformat(),
    },
    {
        "id": "send-3",
        "history_id": "send-3",
        "job_id": HISTORY[0]["job_id"],
        "email": "hello@nordicroast.example",
        "company_name": "Nordic Roast",
        "status": "sent",
        "sent_at": (NOW - timedelta(minutes=7)).isoformat(),
    },
    {
        "id": "send-4",
        "history_id": "send-4",
        "job_id": HISTORY[0]["job_id"],
        "email": "contact@bistrolumen.example",
        "company_name": "Bistro Lumen",
        "status": "sent",
        "sent_at": (NOW - timedelta(minutes=6)).isoformat(),
    },
]

STATS = {
    "total_crawls": 24,
    "total_companies_found": 1284,
    "total_pending": 0,
    "total_running": 0,
    "total_completed": 21,
    "total_failed": 1,
    "total_cancelled": 2,
    "total_email_crawls": 18,
    "total_emails_found": 438,
    "timestamp": NOW.isoformat(),
}

STATUS = {
    "status": "idle",
    "active_jobs": 0,
    "queue_length": 0,
    "total_completed": 21,
    "total_failed": 1,
    "timestamp": NOW.isoformat(),
}

SMTP = {
    "host": "smtp.example.com",
    "port": 587,
    "username": "hello@example.com",
    "password": "",
    "password_set": True,
    "encryption": "starttls",
    "from_name": "Sherlock Maps",
    "from_email": "hello@example.com",
    "enabled": True,
    "test_recipient_email": "test@example.com",
}


def job_results(job_id: str) -> dict:
    job = next((item for item in HISTORY if item["job_id"] == job_id), HISTORY[0])
    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "prompt": job["prompt"],
        "created_at": job["created_at"],
        "completed_at": job["completed_at"],
        "results": COMPANIES,
        "auto_email_crawl": job["auto_email_crawl"],
        "email_job_status": job["email_job_status"],
        "emails_found": job["emails_found"],
    }


def fixture_for(path: str) -> object:
    if path == "/api/stats":
        return STATS
    if path == "/api/status":
        return STATUS
    if path == "/api/crawl/history":
        return {"jobs": HISTORY, "total": len(HISTORY), "limit": 50, "offset": 0}
    if path.startswith("/api/crawl/") and path.endswith("/results"):
        return job_results(path.split("/")[3])
    if path == "/api/templates":
        return TEMPLATES
    if path == "/api/smtp/settings":
        return SMTP
    if path == "/api/email-blacklist":
        return {"entries": BLACKLIST, "total": len(BLACKLIST)}
    if path == "/api/emails/send/history":
        return {"history": SEND_HISTORY, "total": len(SEND_HISTORY), "limit": 100, "offset": 0}
    if path.startswith("/api/emails/recipients/"):
        return RECIPIENTS
    if path.startswith("/api/email-crawl/parent/"):
        return {
            "job_id": "email-" + HISTORY[0]["job_id"],
            "parent_job_id": HISTORY[0]["job_id"],
            "status": "completed",
            "created_at": HISTORY[0]["completed_at"],
            "completed_at": HISTORY[0]["completed_at"],
            "emails_found": 18,
        }
    if path == "/api/crawl":
        return {
            "job_id": "demo-job-000000000000",
            "status": "pending",
            "prompt": "Restaurants Berlin",
            "created_at": NOW.isoformat(),
        }
    if path == "/api/emails/send":
        return {
            "history_id": "send-demo",
            "job_id": HISTORY[0]["job_id"],
            "template_id": TEMPLATES[0]["id"],
            "total_recipients": len(RECIPIENTS),
            "started_at": NOW.isoformat(),
        }
    if path == "/api/health":
        return {"status": "ok", "timestamp": NOW.isoformat(), "version": "1.0.0"}
    return {}


def fulfil(route) -> None:
    path = urlparse(route.request.url).path
    payload = fixture_for(path)
    route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(payload, ensure_ascii=False),
    )


def hide_scrollbars(page: Page) -> None:
    page.add_style_tag(
        content="""
            ::-webkit-scrollbar { display: none; }
            html { scrollbar-width: none; }
            header { position: static !important; }
            [data-testid="recipients-table"] { max-height: none !important; }
            [data-testid="company-results"] { padding: 20px 24px !important; }
        """
    )


def capture(page: Page, path: Path, *, full_page: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(path), full_page=full_page)
    print(f"wrote {path.relative_to(ROOT)}", flush=True)


def capture_locator(locator, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    locator.screenshot(path=str(path))
    print(f"wrote {path.relative_to(ROOT)}", flush=True)


def capture_hero(browser, dashboard_path: Path, output_path: Path) -> None:
    """Frame the dashboard screenshot in a dark, product-launch style browser."""
    encoded = base64.b64encode(dashboard_path.read_bytes()).decode("ascii")
    html = f"""
<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <style>
      * {{ box-sizing: border-box; }}
      html, body {{ margin: 0; width: 2400px; height: 1350px; overflow: hidden; }}
      body {{
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        background:
          radial-gradient(1000px 700px at 50% 42%, rgba(37, 99, 235, .30), transparent 70%),
          linear-gradient(135deg, #050914 0%, #0a1225 55%, #101f45 100%);
      }}
      body::before {{
        content: "";
        position: absolute;
        inset: 0;
        background-image:
          linear-gradient(rgba(255, 255, 255, .035) 1px, transparent 1px),
          linear-gradient(90deg, rgba(255, 255, 255, .035) 1px, transparent 1px);
        background-size: 48px 48px;
        mask-image: linear-gradient(to bottom, rgba(0, 0, 0, .85), transparent 88%);
      }}
      .browser {{
        position: relative;
        width: 2000px;
        overflow: hidden;
        border-radius: 18px;
        background: #0b1220;
        box-shadow:
          0 50px 140px rgba(0, 0, 0, .65),
          0 0 0 1px rgba(255, 255, 255, .12);
      }}
      .bar {{
        height: 62px;
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 0 26px;
        background: linear-gradient(180deg, #111b2e, #0b1220);
        border-bottom: 1px solid rgba(255, 255, 255, .08);
      }}
      .dot {{ width: 12px; height: 12px; border-radius: 50%; }}
      .url {{
        margin-left: 18px;
        flex: 1;
        height: 30px;
        border-radius: 8px;
        background: rgba(255, 255, 255, .06);
        border: 1px solid rgba(255, 255, 255, .08);
        color: #8fa3c8;
        font-size: 12px;
        display: flex;
        align-items: center;
        padding: 0 14px;
        letter-spacing: .02em;
      }}
      .screen {{ padding: 16px; background: #0b1220; }}
      .screen img {{ display: block; width: 100%; border-radius: 10px; }}
    </style>
  </head>
  <body>
    <div class="browser">
      <div class="bar">
        <span class="dot" style="background:#ff5f57"></span>
        <span class="dot" style="background:#febc2e"></span>
        <span class="dot" style="background:#28c840"></span>
        <div class="url">localhost:3008 — Sherlock Maps</div>
      </div>
      <div class="screen"><img src="data:image/png;base64,{encoded}" alt=""></div>
    </div>
  </body>
</html>
"""
    hero_context = browser.new_context(
        viewport={"width": 2400, "height": 1350},
        device_scale_factor=1,
    )
    hero_page = hero_context.new_page()
    hero_page.set_content(html, wait_until="load")
    hero_page.wait_for_function("document.images[0] && document.images[0].complete")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    hero_page.screenshot(path=str(output_path))
    print(f"wrote {output_path.relative_to(ROOT)}", flush=True)
    hero_context.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:3000")
    args = parser.parse_args()

    playwright = sync_playwright().start()
    browser = None
    context = None
    try:
        browser = playwright.chromium.launch()
        context = browser.new_context(
            viewport={"width": 1600, "height": 1000},
            device_scale_factor=2,
            locale="en-US",
            color_scheme="light",
        )
        page = context.new_page()
        page.route("**/api/**", fulfil)
        page.add_init_script("try { localStorage.clear(); } catch (e) {}")

        # Dashboard: top section with KPIs and crawl form.
        page.goto(f"{args.base_url}/", wait_until="networkidle")
        hide_scrollbars(page)
        page.get_by_role("heading", name="Dashboard").wait_for()
        page.locator("#prompt").fill("Restaurants Berlin")
        page.locator('button[aria-label="Toggle email crawling"]').click()
        page.locator('button[aria-label="Use persistent Chrome profile"]').click()
        page.wait_for_timeout(400)
        capture(page, OUTPUT_DIR / "dashboard.png")

        # Results: expand the newest job and show the company table.
        row = page.locator("tr", has_text="Restaurants Berlin").first
        row.locator("button").first.click()
        page.get_by_text("Company Results: Restaurants Berlin").wait_for()
        page.get_by_text("Café Morgenrot").first.scroll_into_view_if_needed()
        page.wait_for_timeout(300)
        capture_locator(
            page.get_by_test_id("company-results"),
            OUTPUT_DIR / "results.png",
        )

        # Email campaign: select a job and a template so the recipient preview is visible.
        page.set_viewport_size({"width": 1600, "height": 1120})
        page.goto(f"{args.base_url}/send-email", wait_until="networkidle")
        hide_scrollbars(page)
        page.get_by_role("heading", name="Send Emails").wait_for()
        page.select_option("#send-job", index=1)
        page.select_option("#send-template", index=1)
        page.get_by_text("Template Preview").wait_for()
        page.get_by_text("Will be sent").first.wait_for()
        capture(page, OUTPUT_DIR / "email-campaign.png")

        # Settings: SMTP configuration and template library.
        page.set_viewport_size({"width": 1600, "height": 1000})
        page.goto(f"{args.base_url}/settings", wait_until="networkidle")
        hide_scrollbars(page)
        page.get_by_text("SMTP Settings").wait_for()
        page.get_by_text("Email Templates", exact=True).wait_for()
        capture(page, OUTPUT_DIR / "settings.png")

        capture_hero(browser, OUTPUT_DIR / "dashboard.png", OUTPUT_DIR / "hero.png")
    finally:
        if context is not None:
            context.close()
        if browser is not None:
            browser.close()
        try:
            playwright.stop()
        except Exception:
            # Some Playwright/Python combinations raise a noisy event-loop
            # error during interpreter shutdown. Resources are already closed.
            pass


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        os._exit(1)
    os._exit(0)
