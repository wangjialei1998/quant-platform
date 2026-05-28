import hashlib
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.strategy import Strategy
from app.schemas.strategy import StrategyCreate, StrategyUpdate
from app.utils.errors import NotFoundError


class StrategyService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, payload: StrategyCreate) -> Strategy:
        code_hash = hashlib.sha256(payload.code.encode("utf-8")).hexdigest()
        strategy = Strategy(
            name=payload.name,
            description=payload.description,
            code_path="pending",
            code_hash=code_hash,
            test_status="pending",
        )
        self.db.add(strategy)
        self.db.flush()

        code_path = self._write_code_file(strategy.id, payload.code)
        strategy.code_path = str(code_path)
        self.db.commit()
        self.db.refresh(strategy)
        return strategy

    def update(self, strategy_id: int, payload: StrategyUpdate) -> Strategy:
        strategy = self.db.get(Strategy, strategy_id)
        if not strategy:
            raise NotFoundError("Strategy not found")

        if payload.name is not None:
            strategy.name = payload.name
        if payload.description is not None:
            strategy.description = payload.description
        if payload.code is not None:
            strategy.code_hash = hashlib.sha256(payload.code.encode("utf-8")).hexdigest()
            strategy.code_path = str(self._write_code_file(strategy.id, payload.code))
            strategy.test_status = "pending"
            strategy.test_log = None
        self.db.commit()
        self.db.refresh(strategy)
        return strategy

    def delete(self, strategy_id: int) -> None:
        strategy = self.db.get(Strategy, strategy_id)
        if not strategy:
            raise NotFoundError("Strategy not found")
        self.db.delete(strategy)
        self.db.commit()

    def _write_code_file(self, strategy_id: int, code: str) -> Path:
        path = settings.strategy_storage_dir / f"strategy_{strategy_id}.py"
        path.write_text(code, encoding="utf-8")
        return path

