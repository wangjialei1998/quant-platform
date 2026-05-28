from sqlalchemy import select

from app.models.instrument import Instrument
from app.repositories.base import Repository


class InstrumentRepository(Repository[Instrument]):
    model = Instrument

    def get_by_symbol(self, symbol: str) -> Instrument | None:
        return self.db.scalar(select(Instrument).where(Instrument.symbol == symbol))

