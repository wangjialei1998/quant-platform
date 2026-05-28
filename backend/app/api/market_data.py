from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.market_data import MarketDailyBar
from app.schemas.market_data import MarketDailyBarRead, MarketDataRangeRead
from app.services.market_data_service import MarketDataService

router = APIRouter()


@router.get("/ranges", response_model=list[MarketDataRangeRead])
def get_ranges(db: Session = Depends(get_db)) -> list[dict]:
    return MarketDataService(db).ranges()


@router.get("/bars", response_model=list[MarketDailyBarRead])
def get_bars(
    instrument_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
) -> list[MarketDailyBar]:
    query = db.query(MarketDailyBar).filter(MarketDailyBar.instrument_id == instrument_id)
    if start_date:
        query = query.filter(MarketDailyBar.trade_date >= start_date)
    if end_date:
        query = query.filter(MarketDailyBar.trade_date <= end_date)
    return query.order_by(MarketDailyBar.trade_date).limit(1000).all()


@router.delete("/bars")
def delete_bars(instrument_id: int, start_date: date, end_date: date, db: Session = Depends(get_db)) -> dict:
    deleted = MarketDataService(db).delete_bars(instrument_id, start_date, end_date)
    return {"message": "ok", "deleted": deleted}

