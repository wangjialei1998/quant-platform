from dataclasses import dataclass
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.instrument import Instrument
from app.models.market_data import MarketDailyBar
from app.models.portfolio import Portfolio, PortfolioInstrument
from app.services.market_data_service import MarketDataService


@dataclass(frozen=True)
class MarketDataSyncItem:
    instrument: Instrument
    start_date: date


class MarketDataSyncService:
    def __init__(self, db: Session):
        self.db = db

    def sync_running_portfolio_bars(self, end_date: date, retry_on_rate_limit: bool = True) -> dict:
        items = [
            MarketDataSyncItem(instrument=item.instrument, start_date=end_date)
            for item in self._running_portfolio_items()
        ]
        return self._sync_items(items, end_date, retry_on_rate_limit)

    def sync_portfolio_bars(self, portfolio_id: int, end_date: date, retry_on_rate_limit: bool = True) -> dict:
        portfolio = self.db.get(Portfolio, portfolio_id)
        if not portfolio:
            return {"status": "failed", "message": "Portfolio not found", "portfolio_id": portfolio_id}
        items = self._portfolio_items(portfolio)
        result = self._sync_items(items, end_date, retry_on_rate_limit)
        result["portfolio_id"] = portfolio_id
        return result

    def sync_cached_bars(self, end_date: date, retry_on_rate_limit: bool = True) -> dict:
        items = self._cached_items()
        return self._sync_items(items, end_date, retry_on_rate_limit)

    def _running_portfolio_items(self) -> list[MarketDataSyncItem]:
        rows = (
            self.db.query(Instrument, func.min(Portfolio.start_date))
            .join(PortfolioInstrument, PortfolioInstrument.instrument_id == Instrument.id)
            .join(Portfolio, Portfolio.id == PortfolioInstrument.portfolio_id)
            .filter(Portfolio.status == "running", Instrument.is_active.is_(True))
            .group_by(Instrument.id)
            .order_by(Instrument.symbol)
            .all()
        )
        return [
            MarketDataSyncItem(instrument=instrument, start_date=start_date)
            for instrument, start_date in rows
            if start_date is not None
        ]

    def _portfolio_items(self, portfolio: Portfolio) -> list[MarketDataSyncItem]:
        instruments = (
            self.db.query(Instrument)
            .join(PortfolioInstrument, PortfolioInstrument.instrument_id == Instrument.id)
            .filter(PortfolioInstrument.portfolio_id == portfolio.id, Instrument.is_active.is_(True))
            .order_by(PortfolioInstrument.sort_order, PortfolioInstrument.id)
            .all()
        )
        return [
            MarketDataSyncItem(instrument=instrument, start_date=portfolio.start_date)
            for instrument in instruments
        ]

    def _cached_items(self) -> list[MarketDataSyncItem]:
        rows = (
            self.db.query(Instrument, func.min(MarketDailyBar.trade_date))
            .join(MarketDailyBar, MarketDailyBar.instrument_id == Instrument.id)
            .filter(Instrument.is_active.is_(True))
            .group_by(Instrument.id)
            .order_by(Instrument.symbol)
            .all()
        )
        return [
            MarketDataSyncItem(instrument=instrument, start_date=start_date)
            for instrument, start_date in rows
            if start_date is not None
        ]

    def _sync_items(
        self,
        items: list[MarketDataSyncItem],
        end_date: date,
        retry_on_rate_limit: bool,
    ) -> dict:
        service = MarketDataService(self.db)
        results: list[dict] = []
        for item in items:
            result = service.ensure_daily_bars(
                [item.instrument],
                item.start_date,
                end_date,
                retry_on_rate_limit=retry_on_rate_limit,
            )
            self.db.commit()
            results.extend(result.get("items", []))
        return {
            "status": "success",
            "end_date": end_date.isoformat(),
            "instrument_count": len(items),
            "items": results,
        }
