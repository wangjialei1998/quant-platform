from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.strategy import Strategy
from app.schemas.common import MessageResponse, TaskResponse
from app.schemas.strategy import StrategyCreate, StrategyRead, StrategyUpdate
from app.services.strategy_service import StrategyService
from app.tasks.strategy_tasks import test_strategy
from app.utils.errors import NotFoundError

router = APIRouter()


@router.get("", response_model=list[StrategyRead])
def list_strategies(db: Session = Depends(get_db)) -> list[Strategy]:
    return db.query(Strategy).order_by(Strategy.created_at.desc()).all()


@router.post("", response_model=StrategyRead)
def create_strategy(payload: StrategyCreate, db: Session = Depends(get_db)) -> Strategy:
    return StrategyService(db).create(payload)


@router.post("/upload", response_model=StrategyRead)
async def upload_strategy(
    name: str = Form(...),
    description: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> Strategy:
    if not file.filename or not file.filename.endswith(".py"):
        raise HTTPException(status_code=400, detail="只支持上传 .py 策略文件")
    code = (await file.read()).decode("utf-8")
    return StrategyService(db).create(StrategyCreate(name=name, description=description, code=code))


@router.get("/{strategy_id}", response_model=StrategyRead)
def get_strategy(strategy_id: int, db: Session = Depends(get_db)) -> Strategy:
    strategy = db.get(Strategy, strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return strategy


@router.patch("/{strategy_id}", response_model=StrategyRead)
def update_strategy(strategy_id: int, payload: StrategyUpdate, db: Session = Depends(get_db)) -> Strategy:
    try:
        return StrategyService(db).update(strategy_id, payload)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{strategy_id}", response_model=MessageResponse)
def delete_strategy(strategy_id: int, db: Session = Depends(get_db)) -> MessageResponse:
    try:
        StrategyService(db).delete(strategy_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return MessageResponse()


@router.post("/{strategy_id}/test", response_model=TaskResponse)
def submit_strategy_test(strategy_id: int, db: Session = Depends(get_db)) -> TaskResponse:
    if not db.get(Strategy, strategy_id):
        raise HTTPException(status_code=404, detail="Strategy not found")
    result = test_strategy.delay(strategy_id)
    return TaskResponse(task_id=result.id)
