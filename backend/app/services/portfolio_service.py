from decimal import Decimal

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.backtest import BacktestRun
from app.models.chart import ChartSnapshot
from app.models.instrument import Instrument
from app.models.log import SystemLog
from app.models.metric import PortfolioMetric
from app.models.notification import Notification
from app.models.portfolio import Portfolio, PortfolioInstrument, PortfolioPosition
from app.models.signal import Signal
from app.models.strategy import Strategy
from app.models.trade import CashFlow, Trade
from app.schemas.portfolio import PortfolioCreate, PortfolioUpdate
from app.utils.errors import NotFoundError, ValidationError


class PortfolioService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, payload: PortfolioCreate) -> Portfolio:
        if not self.db.get(Strategy, payload.strategy_id):
            raise ValidationError("Strategy not found")
        instrument_ids = self._validate_instruments(payload.instrument_ids)

        portfolio = Portfolio(
            name=payload.name,
            strategy_id=payload.strategy_id,
            initial_cash=payload.initial_cash,
            start_date=payload.start_date,
            status="initializing",
            email_enabled=payload.email_enabled,
            commission_rate=payload.commission_rate or Decimal(str(settings.default_commission_rate)),
            stamp_tax_rate=payload.stamp_tax_rate or Decimal(str(settings.default_stamp_tax_rate)),
            slippage_rate=payload.slippage_rate or Decimal(str(settings.default_slippage_rate)),
        )
        self.db.add(portfolio)
        self.db.flush()
        for instrument_id in instrument_ids:
            portfolio_instrument = PortfolioInstrument(
                portfolio_id=portfolio.id,
                instrument_id=instrument_id,
            )
            self.db.add(portfolio_instrument)
        self.db.commit()
        self.db.refresh(portfolio)
        return portfolio

    def set_status(self, portfolio_id: int, status: str) -> Portfolio:
        portfolio = self.db.get(Portfolio, portfolio_id)
        if not portfolio:
            raise NotFoundError("Portfolio not found")
        portfolio.status = status
        self.db.commit()
        self.db.refresh(portfolio)
        return portfolio

    def update(self, portfolio_id: int, payload: PortfolioUpdate) -> Portfolio:
        portfolio = self.db.get(Portfolio, portfolio_id)
        if not portfolio:
            raise NotFoundError("Portfolio not found")
        if not self.db.get(Strategy, payload.strategy_id):
            raise ValidationError("Strategy not found")
        instrument_ids = self._validate_instruments(payload.instrument_ids)

        portfolio.name = payload.name
        portfolio.strategy_id = payload.strategy_id
        portfolio.initial_cash = payload.initial_cash
        portfolio.start_date = payload.start_date
        portfolio.status = "initializing"
        portfolio.email_enabled = payload.email_enabled
        portfolio.commission_rate = payload.commission_rate or Decimal(str(settings.default_commission_rate))
        portfolio.stamp_tax_rate = payload.stamp_tax_rate or Decimal(str(settings.default_stamp_tax_rate))
        portfolio.slippage_rate = payload.slippage_rate or Decimal(str(settings.default_slippage_rate))

        self._clear_derived_outputs(portfolio_id)
        self.db.execute(delete(PortfolioInstrument).where(PortfolioInstrument.portfolio_id == portfolio_id))
        for instrument_id in instrument_ids:
            self.db.add(PortfolioInstrument(portfolio_id=portfolio_id, instrument_id=instrument_id))
        self.db.commit()
        self.db.refresh(portfolio)
        return portfolio

    def _validate_instruments(self, instrument_ids: list[int]) -> list[int]:
        unique_ids = list(dict.fromkeys(instrument_ids))
        rows = self.db.query(Instrument.id).filter(Instrument.id.in_(unique_ids or [0])).all()
        existing_ids = {row[0] for row in rows}
        missing_ids = [instrument_id for instrument_id in unique_ids if instrument_id not in existing_ids]
        if missing_ids:
            raise ValidationError(f"Instrument not found: {', '.join(str(item) for item in missing_ids)}")
        return unique_ids

    def _clear_derived_outputs(self, portfolio_id: int) -> None:
        for model in (
            ChartSnapshot,
            Notification,
            PortfolioMetric,
            PortfolioPosition,
            CashFlow,
            Trade,
            Signal,
        ):
            self.db.execute(delete(model).where(model.portfolio_id == portfolio_id))

    def delete(self, portfolio_id: int) -> None:
        portfolio = self.db.get(Portfolio, portfolio_id)
        if not portfolio:
            raise NotFoundError("Portfolio not found")

        for model in (
            ChartSnapshot,
            Notification,
            SystemLog,
            PortfolioMetric,
            PortfolioPosition,
            CashFlow,
            Trade,
            Signal,
            BacktestRun,
            PortfolioInstrument,
        ):
            self.db.execute(delete(model).where(model.portfolio_id == portfolio_id))

        self.db.delete(portfolio)
        self.db.commit()
