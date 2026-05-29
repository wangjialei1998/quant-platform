from datetime import datetime

from pydantic import Field

from app.schemas.common import OrmModel


class StrategyCreate(OrmModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    code: str = Field(min_length=1)


class StrategyUpdate(OrmModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    code: str | None = Field(default=None, min_length=1)


class StrategyRead(OrmModel):
    id: int
    name: str
    description: str | None
    code_path: str
    code_hash: str
    test_status: str
    test_log: str | None
    code: str | None = None
    last_tested_at: datetime | None
    created_at: datetime
    updated_at: datetime
