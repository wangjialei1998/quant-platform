from typing import Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

ModelT = TypeVar("ModelT")


class Repository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, db: Session):
        self.db = db

    def get(self, item_id: int) -> ModelT | None:
        return self.db.get(self.model, item_id)

    def list(self, page: int = 1, page_size: int = 20) -> tuple[list[ModelT], int]:
        stmt: Select[tuple[ModelT]] = select(self.model).offset((page - 1) * page_size).limit(page_size)
        total = self.db.scalar(select(func.count()).select_from(self.model)) or 0
        return list(self.db.scalars(stmt)), total

