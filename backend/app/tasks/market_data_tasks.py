from datetime import date

from app.core.database import SessionLocal
from app.models.instrument import Instrument
from app.services.market_data_service import MarketDataService
from app.tasks.celery_app import celery_app


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
        return {"status": "failed", "message": str(exc)}
    finally:
        db.close()
