from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class MessageResponse(BaseModel):
    message: str = "ok"


class TaskResponse(BaseModel):
    task_id: str
    status: str = "pending"


class Pagination(BaseModel):
    page: int
    page_size: int
    total: int


class PaginatedResponse(BaseModel, Generic[T]):
    data: list[T]
    pagination: Pagination


class ApiError(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

