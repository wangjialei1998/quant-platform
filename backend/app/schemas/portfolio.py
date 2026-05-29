from datetime import date, datetime
from decimal import Decimal

from pydantic import Field

from app.schemas.common import OrmModel


class PortfolioCreate(OrmModel):
    name: str = Field(min_length=1, max_length=100)
    strategy_id: int
    instrument_ids: list[int] = Field(min_length=1)
    initial_cash: Decimal = Field(gt=0)
    start_date: date
    email_enabled: bool = True
    commission_rate: Decimal | None = None
    stamp_tax_rate: Decimal | None = None
    slippage_rate: Decimal | None = None


class PortfolioUpdate(OrmModel):
    name: str = Field(min_length=1, max_length=100)
    strategy_id: int
    instrument_ids: list[int] = Field(min_length=1)
    initial_cash: Decimal = Field(gt=0)
    start_date: date
    email_enabled: bool = True
    commission_rate: Decimal | None = None
    stamp_tax_rate: Decimal | None = None
    slippage_rate: Decimal | None = None


class PortfolioRead(OrmModel):
    id: int
    name: str
    strategy_id: int
    initial_cash: Decimal
    start_date: date
    status: str
    email_enabled: bool
    commission_rate: Decimal
    stamp_tax_rate: Decimal
    slippage_rate: Decimal
    last_run_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PortfolioListItem(PortfolioRead):
    strategy_name: str | None = None
    instrument_count: int = 0
    latest_net_value: float = 1.0
    current_total_asset: Decimal
    total_return: float = 0.0
    max_drawdown: float = 0.0
    latest_metric_date: date | None = None


class PortfolioSummary(OrmModel):
    id: int
    name: str
    status: str
    latest_net_value: float = 1.0
    annual_return: float = 0.0
    win_rate: float = 0.0
    profit_loss_ratio: float = 0.0
    sharpe_ratio: float = 0.0
    current_drawdown: float = 0.0
    total_return: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_days: int = 0
    volatility: float = 0.0
    sqn: float = 0.0
    vwr: float = 0.0
    trade_count: int = 0
    running_days: int = 0
    start_date: date | None = None
    updated_at: datetime | None = None
    email_enabled: bool = False
    last_run_at: datetime | None = None
