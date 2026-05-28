from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), index=True, nullable=False)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"), nullable=False)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("backtest_runs.id"))
    signal_id: Mapped[int | None] = mapped_column(ForeignKey("signals.id"))
    signal_date: Mapped[date | None] = mapped_column(Date)
    trade_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    side: Mapped[str] = mapped_column(String(10), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    commission: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    stamp_tax: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    slippage: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    net_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="filled", nullable=False)
    reject_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CashFlow(Base):
    __tablename__ = "cash_flows"

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), index=True, nullable=False)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("backtest_runs.id"))
    flow_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    flow_type: Mapped[str] = mapped_column(String(30), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    available_cash: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    position_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    total_asset: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

