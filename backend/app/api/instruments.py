from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.instrument import Instrument
from app.models.market_data import MarketDailyBar
from app.schemas.instrument import InstrumentCreate, InstrumentRead
from app.services.instrument_service import InstrumentService

router = APIRouter()


@router.get("", response_model=list[InstrumentRead])
def list_instruments(
    instrument_type: str | None = None,
    db: Session = Depends(get_db),
) -> list[Instrument]:
    query = db.query(Instrument).join(MarketDailyBar).distinct()
    if instrument_type:
        query = query.filter(Instrument.instrument_type == instrument_type)
    return query.order_by(Instrument.symbol).all()


@router.post("", response_model=InstrumentRead)
def create_instrument(payload: InstrumentCreate, db: Session = Depends(get_db)) -> Instrument:
    return InstrumentService(db).create(payload)
