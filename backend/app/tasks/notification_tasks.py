from app.core.database import SessionLocal
from app.integrations.smtp_client import SMTPClient
from app.models.notification import Notification
from app.tasks.celery_app import celery_app
from app.utils.time import utc_now


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
