from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PortfolioMetric(Base):
    __tablename__ = "portfolio_metrics"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "metric_date", name="uq_portfolio_metric_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), index=True, nullable=False)
    metric_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    net_value: Mapped[float] = mapped_column(default=1.0, nullable=False)
    total_return: Mapped[float] = mapped_column(default=0.0, nullable=False)
    annual_return: Mapped[float] = mapped_column(default=0.0, nullable=False)
    win_rate: Mapped[float] = mapped_column(default=0.0, nullable=False)
    profit_loss_ratio: Mapped[float] = mapped_column(default=0.0, nullable=False)
    sharpe_ratio: Mapped[float] = mapped_column(default=0.0, nullable=False)
    current_drawdown: Mapped[float] = mapped_column(default=0.0, nullable=False)
    max_drawdown: Mapped[float] = mapped_column(default=0.0, nullable=False)
    max_drawdown_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    volatility: Mapped[float] = mapped_column(default=0.0, nullable=False)
    sqn: Mapped[float] = mapped_column(default=0.0, nullable=False)
    vwr: Mapped[float] = mapped_column(default=0.0, nullable=False)
    trade_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    running_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

