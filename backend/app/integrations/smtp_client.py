import re
import smtplib
import ssl
from email.message import EmailMessage
from html import unescape

from app.core.config import settings


class SMTPClient:
    def send(
        self,
        subject: str,
        body: str,
        to_address: str | None = None,
        html_body: str | None = None,
    ) -> None:
        config = _email_settings()
        recipient = to_address or config["smtp_to"]
        if not config["smtp_host"] or not recipient:
            raise RuntimeError("SMTP settings are incomplete")

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = config["smtp_from"]
        message["To"] = recipient
        if html_body or _looks_like_html(body):
            html_content = html_body or body
            text_content = body if html_body else _html_to_text(html_content)
            message.set_content(text_content)
            message.add_alternative(html_content, subtype="html")
        else:
            message.set_content(body)

        port = int(config["smtp_port"])
        if _use_ssl(port, config):
            with smtplib.SMTP_SSL(config["smtp_host"], port, timeout=20, context=ssl.create_default_context()) as client:
                if config["smtp_username"]:
                    client.login(config["smtp_username"], config["smtp_password"])
                client.send_message(message)
            return

        with smtplib.SMTP(config["smtp_host"], port, timeout=20) as client:
            if port not in {25, 2525}:
                client.starttls()
            if config["smtp_username"]:
                client.login(config["smtp_username"], config["smtp_password"])
            client.send_message(message)


def _email_settings() -> dict:
    config = {
        "smtp_host": settings.smtp_host,
        "smtp_port": settings.smtp_port,
        "smtp_username": settings.smtp_username,
        "smtp_password": settings.smtp_password,
        "smtp_from": settings.smtp_from,
        "smtp_to": settings.smtp_to,
    }
    try:
        from app.core.database import SessionLocal
        from app.models.setting import SystemSetting

        db = SessionLocal()
        try:
            row = db.query(SystemSetting).filter(SystemSetting.key == "email").first()
            if row and isinstance(row.value, dict):
                for key, value in row.value.items():
                    if value is not None:
                        config[key] = value
        finally:
            db.close()
    except Exception:
        pass
    return config


def _use_ssl(port: int, config: dict) -> bool:
    if str(config.get("smtp_ssl", "")).lower() in {"1", "true", "yes"}:
        return True
    return port in {465, 456}


def _looks_like_html(value: str) -> bool:
    lowered = value.lstrip().lower()
    return lowered.startswith("<!doctype html") or lowered.startswith("<html") or "<body" in lowered


def _html_to_text(value: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", "", value)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|tr|h[1-6]|table)>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
