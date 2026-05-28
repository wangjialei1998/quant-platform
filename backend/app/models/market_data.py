from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class MarketDailyBar(TimestampMixin, Base):
    __tablename__ = "market_daily_bars"
    __table_args__ = (
        UniqueConstraint("instrument_id", "trade_date", "adjustment_type", name="uq_daily_bar"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"), index=True, nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    volume: Mapped[Decimal | None] = mapped_column(Numeric(24, 4))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(24, 4))
    limit_up: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    limit_down: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    is_suspended: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    adjustment_type: Mapped[str] = mapped_column(String(20), default="none", nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="tickflow", nullable=False)

    instrument = relationship("Instrument", back_populates="daily_bars")

