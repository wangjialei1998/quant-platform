from datetime import date
from decimal import Decimal

from app.schemas.common import OrmModel


class MarketDailyBarRead(OrmModel):
    id: int
    instrument_id: int
    trade_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal | None
    amount: Decimal | None
    limit_up: Decimal | None
    limit_down: Decimal | None
    is_suspended: bool
    adjustment_type: str
    source: str


class MarketDataRangeRead(OrmModel):
    instrument_id: int
    symbol: str
    name: str
    start_date: date | None
    end_date: date | None
    bar_count: int

