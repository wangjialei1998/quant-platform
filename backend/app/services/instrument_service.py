from sqlalchemy.orm import Session

from app.integrations.tickflow_client import TickFlowClient, infer_exchange, infer_instrument_type, normalize_symbol
from app.models.instrument import Instrument
from app.repositories.instrument_repo import InstrumentRepository
from app.schemas.instrument import InstrumentCreate


class InstrumentService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = InstrumentRepository(db)

    def create(self, payload: InstrumentCreate) -> Instrument:
        normalized = normalize_symbol(payload.symbol)
        existing = self.repo.get_by_symbol(normalized)
        if existing:
            return existing
        values = payload.model_dump()
        metadata = TickFlowClient().get_instrument(normalized) or {}
        values["symbol"] = normalized
        values["name"] = values.get("name") or metadata.get("name") or normalized
        values["instrument_type"] = values.get("instrument_type") or _normalize_type(metadata.get("type")) or infer_instrument_type(normalized)
        values["exchange"] = values.get("exchange") or metadata.get("exchange") or infer_exchange(normalized)
        instrument = Instrument(**values)
        self.db.add(instrument)
        self.db.commit()
        self.db.refresh(instrument)
        return instrument


def _normalize_type(value: str | None) -> str | None:
    if value in {"stock", "etf", "index"}:
        return value
    if value in {"fund", "ETF"}:
        return "etf"
    return None
