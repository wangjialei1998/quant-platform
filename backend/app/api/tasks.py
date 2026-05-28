from celery.result import AsyncResult
from fastapi import APIRouter

from app.tasks.celery_app import celery_app

router = APIRouter()


@router.get("/{task_id}")
def get_task_status(task_id: str) -> dict:
    result = AsyncResult(task_id, app=celery_app)
    payload = result.result if result.ready() else None
    return {
        "task_id": task_id,
        "status": result.status.lower(),
        "result": payload,
    }

