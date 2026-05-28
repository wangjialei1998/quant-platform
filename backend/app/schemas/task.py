from typing import Any

from pydantic import BaseModel


class TaskStatus(BaseModel):
    task_id: str
    status: str
    result: Any | None = None

