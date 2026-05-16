import logging
import os
from logging.handlers import SMTPHandler
from pathlib import Path
from typing import Optional

import requests

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "banco_agil.log"


class SlackAlertHandler(logging.Handler):
    """Logging handler that sends error and critical logs to a Slack webhook."""

    def __init__(self, webhook_url: str):
        super().__init__()
        self.webhook_url = webhook_url

    def emit(self, record: logging.LogRecord) -> None:
        if not self.webhook_url or record.levelno < logging.ERROR:
            return
        message = self.format(record)
        payload = {"text": f"*Banco Ágil alerta de erro*\n```{message}```"}
        try:
            requests.post(self.webhook_url, json=payload, timeout=5)
        except Exception:
            self.handleError(record)


def _create_smtp_handler() -> Optional[SMTPHandler]:
    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_port = os.getenv("SMTP_PORT", "587").strip()
    smtp_from = os.getenv("SMTP_FROM", "noreply@bancoagil.local").strip()
    smtp_user = os.getenv("SMTP_USERNAME", "").strip()
    smtp_pass = os.getenv("SMTP_PASSWORD", "").strip()
    recipients = os.getenv("ALERT_EMAIL_RECIPIENTS", "").strip()

    if not smtp_host or not recipients:
        return None

    to_addrs = [recipient.strip() for recipient in recipients.split(",") if recipient.strip()]
    if not to_addrs:
        return None

    try:
        mailhost = (smtp_host, int(smtp_port))
    except ValueError:
        mailhost = smtp_host

    credentials = (smtp_user, smtp_pass) if smtp_user and smtp_pass else None

    handler = SMTPHandler(
        mailhost=mailhost,
        fromaddr=smtp_from,
        toaddrs=to_addrs,
        subject="[Banco Ágil] Alerta de exceção crítica",
        credentials=credentials,
        secure=() if smtp_user and smtp_pass else None,
    )
    return handler


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("banco_agil")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    slack_webhook = os.getenv("SLACK_WEBHOOK_URL", "").strip()
    if slack_webhook:
        slack_handler = SlackAlertHandler(slack_webhook)
        slack_handler.setLevel(logging.ERROR)
        slack_handler.setFormatter(formatter)
        logger.addHandler(slack_handler)

    smtp_handler = _create_smtp_handler()
    if smtp_handler is not None:
        smtp_handler.setLevel(logging.ERROR)
        smtp_handler.setFormatter(formatter)
        logger.addHandler(smtp_handler)

    return logger
