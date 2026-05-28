from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SystemLog(Base):
    __tablename__ = "system_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    level: Mapped[str] = mapped_column(String(20), nullable=False)
    module: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[dict | None] = mapped_column(JSON)
    portfolio_id: Mapped[int | None] = mapped_column(ForeignKey("portfolios.id"))
    strategy_id: Mapped[int | None] = mapped_column(ForeignKey("strategies.id"))
    run_id: Mapped[int | None] = mapped_column(ForeignKey("backtest_runs.id"))
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

