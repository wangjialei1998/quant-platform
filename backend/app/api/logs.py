from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.log import SystemLog

router = APIRouter()


@router.get("")
def list_logs(level: str | None = None, db: Session = Depends(get_db)) -> list[dict]:
    query = db.query(SystemLog)
    if level:
        query = query.filter(SystemLog.level == level)
    rows = query.order_by(SystemLog.created_at.desc()).limit(200).all()
    return [
        {
            "id": item.id,
            "level": item.level,
            "module": item.module,
            "message": item.message,
            "context": item.context,
            "created_at": item.created_at,
        }
        for item in rows
    ]

