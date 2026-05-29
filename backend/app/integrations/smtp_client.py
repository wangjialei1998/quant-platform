import smtplib
from email.message import EmailMessage

from app.core.config import settings


class SMTPClient:
    def send(self, subject: str, body: str, to_address: str | None = None) -> None:
        config = _email_settings()
        recipient = to_address or config["smtp_to"]
        if not config["smtp_host"] or not recipient:
            raise RuntimeError("SMTP 配置不完整")

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = config["smtp_from"]
        message["To"] = recipient
        message.set_content(body)

        port = int(config["smtp_port"])
        with smtplib.SMTP(config["smtp_host"], port, timeout=20) as client:
            if port != 25:
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
