"""SMTP email sender for the Google Maps Crawler.

This module provides:
- Persistent storage for SMTP settings and email templates (JSON files on disk).
- Sending emails to crawled contacts using Python's built-in ``smtplib``.
- A background task that sends emails sequentially with rate limiting,
  while recording per-recipient status in a persistent send history.

Settings, templates and send history are stored under the directory
configured via the ``SMTP_DATA_DIR`` environment variable (defaults to
``<project_root>/core/smtp_data``). This keeps them persistent across
container restarts when the directory is mounted as a volume.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
import logging
import os
import smtplib
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path
from typing import Any, Iterator, Optional

from core.api.models import (
    EmailSendHistoryEntry,
    EmailTemplate,
    EmailTemplateCreate,
    EmailTemplateUpdate,
    SmtpEncryption,
    SmtpSettings,
    SmtpSettingsUpdate,
    SmtpTestResponse,
)

logger = logging.getLogger(__name__)

# Placeholders that can be used inside templates and are replaced per recipient.
TEMPLATE_PLACEHOLDERS = {
    "{{company_name}}": "Name of the company",
    "{{company_website}}": "Company website URL",
    "{{company_address}}": "Company address",
    "{{sender_name}}": "Configured sender name",
    "{{sender_email}}": "Configured sender email",
}

MAX_HISTORY_ENTRIES = 500


def default_data_dir() -> str:
    """Return the default directory for persisted mailer data."""
    configured = os.environ.get("SMTP_DATA_DIR", "").strip()
    if configured:
        return configured
    project_core = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(project_core, "smtp_data")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class EmailSenderStore:
    """Persists SMTP settings, templates and send history as JSON files."""

    def __init__(self, data_dir: Optional[str] = None) -> None:
        self.data_dir = Path(data_dir or default_data_dir())
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

        self._smtp: SmtpSettings = SmtpSettings()
        self._templates: dict[str, EmailTemplate] = {}
        self._history: list[EmailSendHistoryEntry] = []
        self._active_sends: set[str] = set()
        self._cancel_events: dict[str, asyncio.Event] = {}
        self._executor: Optional[concurrent.futures.ThreadPoolExecutor] = None

        self._load()

    # ------------------------------------------------------------------ I/O

    def _load(self) -> None:
        settings_file = self.data_dir / "mailer.json"
        if settings_file.exists():
            try:
                raw = json.loads(settings_file.read_text(encoding="utf-8"))
                smtp_raw = raw.get("smtp", {})
                self._smtp = SmtpSettings.model_validate(smtp_raw)
                for tmpl in raw.get("templates", []):
                    template = EmailTemplate.model_validate(tmpl)
                    self._templates[template.id] = template
            except Exception as e:
                logger.error("Failed to load mailer settings: %s", e)

        history_file = self.data_dir / "send_history.json"
        if history_file.exists():
            try:
                raw = json.loads(history_file.read_text(encoding="utf-8"))
                self._history = [
                    EmailSendHistoryEntry.model_validate(entry) for entry in raw
                ]
                # Batches that were still sending when the server stopped cannot
                # resume. Mark any orphaned pending entries as cancelled.
                changed = False
                for entry in self._history:
                    if entry.status == "pending":
                        entry.status = "cancelled"
                        entry.error = "Server restarted while sending"
                        changed = True
                if changed:
                    self._save()
                    logger.info("Marked %d orphaned pending history entries as cancelled", sum(1 for e in self._history if e.status == "cancelled" and e.error == "Server restarted while sending"))
            except Exception as e:
                logger.error("Failed to load send history: %s", e)

    def _save(self) -> None:
        settings_file = self.data_dir / "mailer.json"
        payload = {
            "smtp": self._smtp.model_dump(mode="json"),
            "templates": [t.model_dump(mode="json") for t in self._templates.values()],
        }
        tmp = settings_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(settings_file)

        history_file = self.data_dir / "send_history.json"
        history_payload = [e.model_dump(mode="json") for e in self._history]
        tmp = history_file.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(history_payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(history_file)

    # ----------------------------------------------------------------- SMTP

    def get_smtp(self) -> dict[str, Any]:
        """Return SMTP settings with the password masked unless configured."""
        data = self._smtp.model_dump()
        data["password"] = "********" if self._smtp.password_set else ""
        data["password_set"] = self._smtp.password_set
        return data

    def update_smtp(self, update: SmtpSettingsUpdate) -> dict[str, Any]:
        """Apply a partial update to the SMTP settings."""
        with self._lock:
            values = update.model_dump(exclude_unset=True)
            if "password" in values:
                new_password = values.pop("password")
                if new_password:
                    self._smtp.password = new_password
                    self._smtp.password_set = True
                elif new_password == "":
                    self._smtp.password_set = False
            for key, value in values.items():
                setattr(self._smtp, key, value)
            self._save()
            logger.info("SMTP settings updated")
            return self.get_smtp()

    def test_connection(self, to_email: str) -> SmtpTestResponse:
        """Attempt to connect and send a test email using current settings."""
        smtp = self._smtp
        if not smtp.host:
            return SmtpTestResponse(
                success=False,
                message="SMTP settings are incomplete",
                error="No SMTP host configured",
            )
        from_addr = self._resolve_sender()
        try:
            with _smtp_connect(smtp) as server:
                message = EmailMessage()
                message["From"] = from_addr
                message["To"] = to_email
                message["Subject"] = "Test email from Google Maps Crawler"
                message.set_content(
                    "This is a test message from the Google Maps Crawler.\n"
                    "Your SMTP settings are working correctly."
                )
                server.send_message(message)
            return SmtpTestResponse(
                success=True,
                message=f"Test email sent to {to_email}",
            )
        except Exception as e:
            logger.warning("SMTP test failed: %s", e)
            return SmtpTestResponse(
                success=False,
                message="SMTP test failed",
                error=str(e),
            )

    def _resolve_sender(self) -> str:
        """Build the ``From`` address from SMTP settings."""
        from_email = self._smtp.from_email or self._smtp.username
        from_name = self._smtp.from_name
        if from_name and from_email:
            return formataddr((from_name, from_email))
        return from_email or ""

    # -------------------------------------------------------------- Templates

    def list_templates(self) -> list[dict[str, Any]]:
        with self._lock:
            templates = sorted(
                (t.model_dump() for t in self._templates.values()),
                key=lambda t: t["updated_at"],
                reverse=True,
            )
            return templates

    def get_template(self, template_id: str) -> Optional[EmailTemplate]:
        with self._lock:
            return self._templates.get(template_id)

    def create_template(self, data: EmailTemplateCreate) -> EmailTemplate:
        now = datetime.now(timezone.utc)
        template = EmailTemplate(
            id=str(uuid.uuid4()),
            name=data.name.strip(),
            subject=data.subject.strip(),
            body=data.body,
            html=data.html,
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._templates[template.id] = template
            self._save()
        logger.info("Created email template: %s", template.name)
        return template

    def update_template(
        self, template_id: str, data: EmailTemplateUpdate
    ) -> Optional[EmailTemplate]:
        with self._lock:
            template = self._templates.get(template_id)
            if not template:
                return None
            values = data.model_dump(exclude_unset=True)
            for key, value in values.items():
                setattr(template, key, value)
            template.updated_at = datetime.now(timezone.utc)
            self._save()
        logger.info("Updated email template: %s", template.name)
        return template

    def delete_template(self, template_id: str) -> bool:
        with self._lock:
            existed = self._templates.pop(template_id, None) is not None
            if existed:
                self._save()
        logger.info("Deleted email template: %s", template_id)
        return existed

    # ---------------------------------------------------------------- Sending

    def create_send(
        self,
        job_id: str,
        template: EmailTemplate,
        recipients: list[dict[str, Any]],
        test: bool = False,
    ) -> str:
        """Create a send history batch and return its history_id."""
        history_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        with self._lock:
            for recipient in recipients:
                self._history.append(
                    EmailSendHistoryEntry(
                        id=str(uuid.uuid4()),
                        history_id=history_id,
                        job_id=job_id,
                        email=recipient["email"],
                        company_name=recipient.get("company_name", ""),
                        status="pending",
                        sent_at=None,
                    )
                )
            self._cancel_events[history_id] = asyncio.Event()
            self._trim_history()
            self._save()
        return history_id

    def _trim_history(self) -> None:
        if len(self._history) > MAX_HISTORY_ENTRIES:
            self._history = self._history[-MAX_HISTORY_ENTRIES:]

    def get_history(
        self, limit: int = 50, offset: int = 0
    ) -> tuple[list[EmailSendHistoryEntry], int]:
        with self._lock:
            entries = list(reversed(self._history))
            total = len(entries)
            return entries[offset : offset + limit], total

    def clear_history(self) -> int:
        """Delete the entire send history.

        Returns:
            The number of entries that were removed.
        """
        with self._lock:
            count = len(self._history)
            self._history = []
            self._cancel_events.clear()
            self._active_sends.clear()
            self._save()
            logger.info("Cleared send history (%d entries removed)", count)
            return count

    def set_entry_status(
        self,
        history_id: str,
        email: str,
        status: str,
        error: Optional[str] = None,
    ) -> None:
        with self._lock:
            for entry in self._history:
                if entry.history_id == history_id and entry.email == email:
                    entry.status = status
                    entry.error = error
                    if status == "sent":
                        entry.sent_at = datetime.now(timezone.utc)
                    break
            self._save()

    def _cancel_pending(self, history_id: str) -> None:
        """Mark all still-pending entries of a batch as cancelled."""
        for entry in self._history:
            if entry.history_id == history_id and entry.status == "pending":
                entry.status = "cancelled"
                entry.error = "Send batch cancelled by user"
        self._save()

    def _fail_pending(self, history_id: str, error: str) -> None:
        """Mark all still-pending entries of a batch as failed."""
        for entry in self._history:
            if entry.history_id == history_id and entry.status == "pending":
                entry.status = "failed"
                entry.error = error
        self._save()

    def cancel_send(self, history_id: str) -> bool:
        """Cancel a running send batch.

        Signals the background send loop to stop and marks all remaining
        pending entries as cancelled. Also works for orphaned batches whose
        background task no longer exists (e.g. after a server restart).

        Returns:
            True if the batch exists in the history (cancelled or already
            finished), False if the batch is completely unknown.
        """
        with self._lock:
            exists_in_history = any(
                e.history_id == history_id for e in self._history
            )
            if not exists_in_history:
                return False

            event = self._cancel_events.get(history_id)
            if event is not None:
                event.set()
            self._cancel_pending(history_id)
            logger.info("Cancelled send batch %s", history_id[:8])
            return True

    async def process_send(
        self,
        history_id: str,
        template: EmailTemplate,
        recipients: list[dict[str, Any]],
        delay_seconds: float,
        test: bool = False,
    ) -> None:
        """Send emails to all recipients in the background.

        Emails are sent sequentially with a configurable delay. In ``test``
        mode every personalized email is sent to the configured test recipient
        address instead of the real recipient.
        """
        self._active_sends.add(history_id)
        cancel_event = self._cancel_events.get(history_id) or asyncio.Event()
        self._cancel_events[history_id] = cancel_event
        try:
            smtp = self._smtp
            if not smtp.host or not smtp.enabled:
                error = "SMTP not configured or sending is disabled"
                for recipient in recipients:
                    self.set_entry_status(
                        history_id, recipient["email"], "failed", error=error
                    )
                return

            sender = self._resolve_sender()
            loop = asyncio.get_running_loop()
            if self._executor is None:
                self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

            for recipient in recipients:
                if cancel_event.is_set():
                    logger.info("Send batch %s cancelled", history_id[:8])
                    self._cancel_pending(history_id)
                    return

                try:
                    to_email = smtp.test_recipient_email.strip() if test else recipient["email"]
                    body = render_template(template.body, recipient, smtp)
                    subject = render_template(template.subject, recipient, smtp)

                    await loop.run_in_executor(
                        self._executor,
                        _send_single,
                        smtp,
                        sender,
                        to_email,
                        subject,
                        body,
                        template.html,
                    )
                    self.set_entry_status(history_id, recipient["email"], "sent")
                except Exception as e:
                    logger.warning("Failed to send to %s: %s", recipient.get("email"), e)
                    self.set_entry_status(
                        history_id, recipient["email"], "failed", error=str(e)
                    )

                if delay_seconds > 0 and not cancel_event.is_set():
                    try:
                        await asyncio.wait_for(cancel_event.wait(), timeout=delay_seconds)
                    except asyncio.TimeoutError:
                        pass

            if cancel_event.is_set():
                logger.info("Send batch %s cancelled", history_id[:8])
                self._cancel_pending(history_id)
            else:
                logger.info("Send batch %s finished", history_id[:8])
        except asyncio.CancelledError:
            self._cancel_pending(history_id)
            raise
        except Exception as e:
            logger.exception("Send batch %s failed unexpectedly: %s", history_id[:8], e)
            self._fail_pending(history_id, f"Send batch failed: {e}")
        finally:
            self._active_sends.discard(history_id)
            self._cancel_events.pop(history_id, None)


def render_template(
    text: str,
    recipient: dict[str, Any],
    smtp: SmtpSettings,
) -> str:
    """Replace template placeholders with recipient/sender values."""
    replacements = {
        "{{company_name}}": recipient.get("company_name", ""),
        "{{company_website}}": recipient.get("company_website", ""),
        "{{company_address}}": recipient.get("company_address", ""),
        "{{sender_name}}": smtp.from_name or "",
        "{{sender_email}}": smtp.from_email or smtp.username or "",
    }
    for placeholder, value in replacements.items():
        text = text.replace(placeholder, value or "")
    return text


def _send_single(
    smtp: SmtpSettings,
    sender: str,
    to_email: str,
    subject: str,
    body: str,
    html: bool,
) -> None:
    """Send a single email over SMTP (runs in a worker thread)."""
    message = EmailMessage()
    message["From"] = sender
    message["To"] = to_email
    message["Subject"] = subject
    if html:
        message.add_alternative(body, subtype="html")
    else:
        message.set_content(body)

    with _smtp_connect(smtp) as server:
        server.send_message(message)


@contextmanager
def _smtp_connect(smtp: SmtpSettings):
    """Connect to an SMTP server applying the configured encryption."""
    if smtp.encryption == SmtpEncryption.SSL:
        server = smtplib.SMTP_SSL(smtp.host, smtp.port, timeout=30)
    else:
        server = smtplib.SMTP(smtp.host, smtp.port, timeout=30)
        server.ehlo()
        if smtp.encryption == SmtpEncryption.STARTTLS:
            server.starttls()
            server.ehlo()

    try:
        if smtp.username:
            server.login(smtp.username, smtp.password or "")
        yield server
    finally:
        try:
            server.quit()
        except Exception:
            try:
                server.close()
            except Exception:
                pass
