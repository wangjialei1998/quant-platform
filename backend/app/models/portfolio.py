from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class Portfolio(TimestampMixin, Base):
    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    strategy_id: Mapped[int] = mapped_column(ForeignKey("strategies.id"), nullable=False)
    initial_cash: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="initializing", nullable=False)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    commission_rate: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    stamp_tax_rate: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    slippage_rate: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    strategy = relationship("Strategy", back_populates="portfolios")
    instruments = relationship("PortfolioInstrument", back_populates="portfolio", cascade="all, delete-orphan")


class PortfolioInstrument(Base):
    __tablename__ = "portfolio_instruments"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "instrument_id", name="uq_portfolio_instrument"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), nullable=False)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    portfolio = relationship("Portfolio", back_populates="instruments")
    instrument = relationship("Instrument")


class PortfolioPosition(Base):
    __tablename__ = "portfolio_positions"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "instrument_id", "trade_date", name="uq_position_snapshot"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), index=True, nullable=False)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    sellable_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    cost_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    market_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    weight: Mapped[float] = mapped_column(default=0.0, nullable=False)
