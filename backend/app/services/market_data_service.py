from datetime import date

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.integrations.tickflow_client import TickFlowClient
from app.models.instrument import Instrument
from app.models.market_data import MarketDailyBar
from app.utils.trading_calendar import next_or_same_trading_day, previous_or_same_trading_day, trading_day_count


class MarketDataService:
    def __init__(self, db: Session, tickflow_client: TickFlowClient | None = None):
        self.db = db
        self.tickflow_client = tickflow_client or TickFlowClient()

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
            .join(MarketDailyBar, MarketDailyBar.instrument_id == Instrument.id)
            .group_by(Instrument.id)
            .having(func.count(MarketDailyBar.id) > 0)
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

    def ensure_daily_bars(
        self,
        instruments: list[Instrument],
        start_date: date,
        end_date: date,
        adjustment_type: str = "none",
    ) -> dict:
        synced: list[dict] = []
        sync_start_date = next_or_same_trading_day(start_date)
        sync_end_date = previous_or_same_trading_day(end_date)
        for instrument in instruments:
            if sync_start_date > sync_end_date:
                existing_dates = self._existing_dates(instrument.id, start_date, end_date, adjustment_type)
                synced.append(
                    {
                        "instrument_id": instrument.id,
                        "symbol": instrument.symbol,
                        "fetched": 0,
                        "cached": len(existing_dates),
                    }
                )
                continue

            existing_dates = self._existing_dates(instrument.id, sync_start_date, sync_end_date, adjustment_type)
            if existing_dates:
                missing_start = sync_start_date if min(existing_dates) > sync_start_date else None
                missing_end = sync_end_date if max(existing_dates) < sync_end_date else None
                cached_start = min(existing_dates)
                cached_end = max(existing_dates)
                full_span_cached = (
                    cached_start <= sync_start_date
                    and cached_end >= sync_end_date
                    and len(existing_dates) >= trading_day_count(sync_start_date, sync_end_date) * 0.6
                )
                if missing_start is None and missing_end is None and full_span_cached:
                    synced.append(
                        {
                            "instrument_id": instrument.id,
                            "symbol": instrument.symbol,
                            "fetched": 0,
                            "cached": len(existing_dates),
                        }
                    )
                    continue

            fetched = self.tickflow_client.fetch_daily_bars(instrument.symbol, sync_start_date, sync_end_date)
            saved = self._upsert_bars(instrument, fetched, adjustment_type)
            synced.append(
                {
                    "instrument_id": instrument.id,
                    "symbol": instrument.symbol,
                    "fetched": len(fetched),
                    "saved": saved,
                }
            )
            if not fetched and not existing_dates:
                raise RuntimeError(f"No daily bars returned for {instrument.symbol} from TickFlow")
        self.db.flush()
        return {"status": "success", "items": synced}

    def _existing_dates(
        self,
        instrument_id: int,
        start_date: date,
        end_date: date,
        adjustment_type: str,
    ) -> set[date]:
        rows = (
            self.db.query(MarketDailyBar.trade_date)
            .filter(
                MarketDailyBar.instrument_id == instrument_id,
                MarketDailyBar.trade_date >= start_date,
                MarketDailyBar.trade_date <= end_date,
                MarketDailyBar.adjustment_type == adjustment_type,
            )
            .all()
        )
        return {row[0] for row in rows}

    def _upsert_bars(self, instrument: Instrument, bars: list[dict], adjustment_type: str) -> int:
        if not bars:
            return 0

        dates = [bar["trade_date"] for bar in bars]
        existing = {
            row.trade_date: row
            for row in self.db.query(MarketDailyBar)
            .filter(
                MarketDailyBar.instrument_id == instrument.id,
                MarketDailyBar.trade_date.in_(dates),
                MarketDailyBar.adjustment_type == adjustment_type,
            )
            .all()
        }

        saved = 0
        for bar in bars:
            row = existing.get(bar["trade_date"])
            values = {
                "open": bar["open"],
                "high": bar["high"],
                "low": bar["low"],
                "close": bar["close"],
                "volume": bar.get("volume"),
                "amount": bar.get("amount"),
                "limit_up": bar.get("limit_up"),
                "limit_down": bar.get("limit_down"),
                "is_suspended": bar.get("is_suspended", False),
                "source": "tickflow",
            }
            if row:
                for key, value in values.items():
                    setattr(row, key, value)
            else:
                self.db.add(
                    MarketDailyBar(
                        instrument_id=instrument.id,
                        trade_date=bar["trade_date"],
                        adjustment_type=adjustment_type,
                        **values,
                    )
                )
            saved += 1
        return saved
