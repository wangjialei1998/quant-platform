from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.portfolio import Portfolio, PortfolioInstrument
from app.models.strategy import Strategy
from app.schemas.portfolio import PortfolioCreate
from app.utils.errors import NotFoundError, ValidationError


class PortfolioService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, payload: PortfolioCreate) -> Portfolio:
        if not self.db.get(Strategy, payload.strategy_id):
            raise ValidationError("Strategy not found")

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
        for instrument_id in payload.instrument_ids:
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
