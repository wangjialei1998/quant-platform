from sqlalchemy.orm import Session

from app.models.instrument import Instrument
from app.repositories.instrument_repo import InstrumentRepository
from app.schemas.instrument import InstrumentCreate


class InstrumentService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = InstrumentRepository(db)

    def create(self, payload: InstrumentCreate) -> Instrument:
        existing = self.repo.get_by_symbol(payload.symbol)
        if existing:
            return existing
        instrument = Instrument(**payload.model_dump())
        self.db.add(instrument)
        self.db.commit()
        self.db.refresh(instrument)
        return instrument

