from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.models.portfolio import Portfolio
from app.utils.time import utc_now


class NotificationService:
    def __init__(self, db: Session):
        self.db = db

    def create_event(
        self,
        portfolio: Portfolio | None,
        event_type: str,
        title: str,
        content: str,
        should_send: bool = True,
    ) -> Notification:
        notification = Notification(
            portfolio_id=portfolio.id if portfolio else None,
            event_type=event_type,
            channel="email",
            title=title,
            content=content,
            status="pending" if should_send and (portfolio.email_enabled if portfolio else True) else "skipped",
            error_message=None,
            sent_at=None,
            created_at=utc_now(),
        )
        self.db.add(notification)
        self.db.flush()
        return notification

    @staticmethod
    def enqueue(notification_ids: list[int]) -> None:
        from app.tasks.notification_tasks import send_notification

        for notification_id in notification_ids:
            send_notification.delay(notification_id)
