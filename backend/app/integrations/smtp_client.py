import smtplib
from email.message import EmailMessage

from app.core.config import settings


class SMTPClient:
    def send(self, subject: str, body: str, to_address: str | None = None) -> None:
        recipient = to_address or settings.smtp_to
        if not settings.smtp_host or not recipient:
            raise RuntimeError("SMTP 配置不完整")

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = settings.smtp_from
        message["To"] = recipient
        message.set_content(body)

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as client:
            client.starttls()
            if settings.smtp_username:
                client.login(settings.smtp_username, settings.smtp_password)
            client.send_message(message)

