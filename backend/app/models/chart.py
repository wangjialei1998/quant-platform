from datetime import date

from sqlalchemy import Date, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin


class ChartSnapshot(TimestampMixin, Base):
    __tablename__ = "chart_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), index=True, nullable=False)
    chart_type: Mapped[str] = mapped_column(String(50), nullable=False)
    range_start: Mapped[date | None] = mapped_column(Date)
    range_end: Mapped[date | None] = mapped_column(Date)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)

