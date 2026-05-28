from datetime import datetime

from pydantic import Field

from app.schemas.common import OrmModel


class InstrumentCreate(OrmModel):
    symbol: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=100)
    instrument_type: str = Field(pattern="^(stock|etf|index)$")
    exchange: str = Field(min_length=1, max_length=20)
    is_active: bool = True


class InstrumentRead(OrmModel):
    id: int
    symbol: str
    name: str
    instrument_type: str
    exchange: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

