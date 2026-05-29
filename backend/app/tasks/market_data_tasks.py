from datetime import date

from app.core.database import SessionLocal
from app.models.instrument import Instrument
from app.models.log import SystemLog
from app.models.notification import Notification
from app.services.market_data_service import MarketDataService
from app.tasks.celery_app import celery_app
from app.utils.time import utc_now


@celery_app.task(name="app.tasks.market_data_tasks.sync_market_data")
def sync_market_data(instrument_ids: list[int], start_date: str, end_date: str) -> dict:
    db = SessionLocal()
    try:
        instruments = db.query(Instrument).filter(Instrument.id.in_(instrument_ids or [0])).all()
        result = MarketDataService(db).ensure_daily_bars(
            instruments,
            date.fromisoformat(start_date),
            date.fromisoformat(end_date),
        )
        db.commit()
        return {
            "status": "success",
            "instrument_ids": instrument_ids,
            "start_date": start_date,
            "end_date": end_date,
            **result,
        }
    except Exception as exc:
        db.rollback()
        notification = Notification(
            portfolio_id=None,
            event_type="error",
            channel="email",
            title="行情数据更新失败",
            content=f"标的ID：{instrument_ids}\n日期范围：{start_date} 至 {end_date}\n错误摘要：{exc}",
            status="pending",
            error_message=None,
            sent_at=None,
            created_at=utc_now(),
        )
        db.add(notification)
        db.add(
            SystemLog(
                level="error",
                module="market_data",
                message=str(exc),
                context={"instrument_ids": instrument_ids, "start_date": start_date, "end_date": end_date},
                portfolio_id=None,
                strategy_id=None,
                run_id=None,
                created_at=utc_now(),
            )
        )
        db.commit()
        from app.tasks.notification_tasks import send_notification

        send_notification.delay(notification.id)
        return {"status": "failed", "message": str(exc)}
    finally:
        db.close()
