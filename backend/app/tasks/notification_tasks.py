from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.database import SessionLocal
from app.integrations.smtp_client import SMTPClient
from app.models.notification import Notification
from app.models.portfolio import Portfolio
from app.services.notification_service import NotificationService
from app.services.portfolio_report_email_service import PortfolioReportEmailService
from app.tasks.celery_app import celery_app
from app.utils.time import utc_now
from app.utils.trading_calendar import is_trading_day


@celery_app.task(name="app.tasks.notification_tasks.send_notification", bind=True, max_retries=2, default_retry_delay=30)
def send_notification(self, notification_id: int) -> dict:
    db = SessionLocal()
    try:
        notification = db.get(Notification, notification_id)
        if not notification:
            return {"status": "failed", "notification_id": notification_id, "message": "Notification not found"}
        if notification.status != "pending":
            return {"status": notification.status, "notification_id": notification_id}

        try:
            SMTPClient().send(notification.title, notification.content)
        except Exception as exc:
            notification.error_message = str(exc)
            if self.request.retries >= self.max_retries:
                notification.status = "failed"
                db.commit()
                return {"status": "failed", "notification_id": notification_id, "message": str(exc)}
            db.commit()
            db.close()
            db = None
            # Restore pending before retry so the next attempt is allowed to send.
            retry_db = SessionLocal()
            try:
                retry_notification = retry_db.get(Notification, notification_id)
                if retry_notification:
                    retry_notification.status = "pending"
                    retry_db.commit()
            finally:
                retry_db.close()
            raise self.retry(exc=exc)

        notification.status = "sent"
        notification.sent_at = utc_now()
        notification.error_message = None
        db.commit()
        return {"status": "sent", "notification_id": notification_id}
    finally:
        if db is not None:
            db.close()


@celery_app.task(name="app.tasks.notification_tasks.send_today_trading_day_reports")
def send_today_trading_day_reports() -> dict:
    today = datetime.now(ZoneInfo("Asia/Shanghai")).date()
    if not is_trading_day(today):
        return {"status": "skipped", "message": "today is not a trading day", "date": today.isoformat()}

    report_date = today
    db = SessionLocal()
    try:
        portfolios = (
            db.query(Portfolio)
            .filter(Portfolio.status == "running", Portfolio.email_enabled.is_(True))
            .order_by(Portfolio.id)
            .all()
        )
        service = PortfolioReportEmailService(db)
        notification_ids: list[int] = []
        for portfolio in portfolios:
            notification_id = service.create_report_notification(
                portfolio,
                force=True,
                report_date=report_date,
            )
            if notification_id:
                notification_ids.append(notification_id)
        db.commit()
        NotificationService.enqueue(notification_ids)
        return {
            "status": "submitted",
            "report_date": report_date.isoformat(),
            "portfolio_count": len(portfolios),
            "notification_ids": notification_ids,
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
