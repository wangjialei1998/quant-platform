from datetime import date

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.instrument import Instrument
from app.models.market_data import MarketDailyBar


class MarketDataService:
    def __init__(self, db: Session):
        self.db = db

    def ranges(self) -> list[dict]:
        stmt = (
            select(
                Instrument.id,
                Instrument.symbol,
                Instrument.name,
                func.min(MarketDailyBar.trade_date),
                func.max(MarketDailyBar.trade_date),
                func.count(MarketDailyBar.id),
            )
            .outerjoin(MarketDailyBar, MarketDailyBar.instrument_id == Instrument.id)
            .group_by(Instrument.id)
            .order_by(Instrument.symbol)
        )
        return [
            {
                "instrument_id": row[0],
                "symbol": row[1],
                "name": row[2],
                "start_date": row[3],
                "end_date": row[4],
                "bar_count": row[5],
            }
            for row in self.db.execute(stmt).all()
        ]

    def delete_bars(self, instrument_id: int, start_date: date, end_date: date) -> int:
        stmt = delete(MarketDailyBar).where(
            MarketDailyBar.instrument_id == instrument_id,
            MarketDailyBar.trade_date >= start_date,
            MarketDailyBar.trade_date <= end_date,
        )
        result = self.db.execute(stmt)
        self.db.commit()
        return result.rowcount or 0

