from datetime import date
from decimal import Decimal

from app.schemas.common import OrmModel


class SignalRead(OrmModel):
    id: int
    portfolio_id: int
    instrument_id: int
    signal_date: date
    side: str
    price: Decimal
    status: str
    email_status: str

