from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.metric import PortfolioMetric
from app.models.portfolio import Portfolio, PortfolioPosition
from app.models.trade import CashFlow, Trade
from app.schemas.common import MessageResponse, TaskResponse
from app.schemas.portfolio import PortfolioCreate, PortfolioRead, PortfolioSummary
from app.services.portfolio_service import PortfolioService
from app.tasks.backtest_tasks import initialize_portfolio
from app.tasks.monitor_tasks import monitor_portfolio
from app.utils.errors import NotFoundError, ValidationError

router = APIRouter()


@router.get("", response_model=list[PortfolioRead])
def list_portfolios(db: Session = Depends(get_db)) -> list[Portfolio]:
    return db.query(Portfolio).order_by(Portfolio.created_at.desc()).all()


@router.post("", response_model=TaskResponse)
def create_portfolio(payload: PortfolioCreate, db: Session = Depends(get_db)) -> TaskResponse:
    try:
        portfolio = PortfolioService(db).create(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    task = initialize_portfolio.delay(portfolio.id)
    return TaskResponse(task_id=task.id)


@router.get("/{portfolio_id}", response_model=PortfolioRead)
def get_portfolio(portfolio_id: int, db: Session = Depends(get_db)) -> Portfolio:
    portfolio = db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio


@router.delete("/{portfolio_id}", response_model=MessageResponse)
def delete_portfolio(portfolio_id: int, db: Session = Depends(get_db)) -> MessageResponse:
    portfolio = db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    portfolio.status = "deleted"
    db.commit()
    return MessageResponse()


@router.post("/{portfolio_id}/pause", response_model=PortfolioRead)
def pause_portfolio(portfolio_id: int, db: Session = Depends(get_db)) -> Portfolio:
    try:
        return PortfolioService(db).set_status(portfolio_id, "paused")
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{portfolio_id}/resume", response_model=PortfolioRead)
def resume_portfolio(portfolio_id: int, db: Session = Depends(get_db)) -> Portfolio:
    try:
        return PortfolioService(db).set_status(portfolio_id, "running")
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{portfolio_id}/run", response_model=TaskResponse)
def run_portfolio(portfolio_id: int, db: Session = Depends(get_db)) -> TaskResponse:
    if not db.get(Portfolio, portfolio_id):
        raise HTTPException(status_code=404, detail="Portfolio not found")
    task = monitor_portfolio.delay(portfolio_id, "manual_monitor")
    return TaskResponse(task_id=task.id)


@router.get("/{portfolio_id}/summary", response_model=PortfolioSummary)
def get_portfolio_summary(portfolio_id: int, db: Session = Depends(get_db)) -> PortfolioSummary:
    portfolio = db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    metric = (
        db.query(PortfolioMetric)
        .filter(PortfolioMetric.portfolio_id == portfolio_id)
        .order_by(PortfolioMetric.metric_date.desc())
        .first()
    )
    return PortfolioSummary(
        id=portfolio.id,
        name=portfolio.name,
        status=portfolio.status,
        latest_net_value=metric.net_value if metric else 1.0,
        total_return=metric.total_return if metric else 0.0,
        max_drawdown=metric.max_drawdown if metric else 0.0,
        trade_count=metric.trade_count if metric else 0,
        last_run_at=portfolio.last_run_at,
    )


@router.get("/{portfolio_id}/metrics")
def get_portfolio_metrics(portfolio_id: int, db: Session = Depends(get_db)) -> list[dict]:
    rows = db.query(PortfolioMetric).filter(PortfolioMetric.portfolio_id == portfolio_id).all()
    return [
        {
            "date": item.metric_date,
            "net_value": item.net_value,
            "total_return": item.total_return,
            "max_drawdown": item.max_drawdown,
        }
        for item in rows
    ]


@router.get("/{portfolio_id}/equity-curve")
def get_equity_curve(portfolio_id: int) -> dict:
    return {"dates": [], "portfolio": [], "benchmark": []}


@router.get("/{portfolio_id}/drawdown")
def get_drawdown(portfolio_id: int) -> dict:
    return {"dates": [], "drawdown": []}


@router.get("/{portfolio_id}/positions")
def get_positions(portfolio_id: int, db: Session = Depends(get_db)) -> list[dict]:
    rows = db.query(PortfolioPosition).filter(PortfolioPosition.portfolio_id == portfolio_id).limit(500).all()
    return [
        {
            "date": item.trade_date,
            "instrument_id": item.instrument_id,
            "quantity": item.quantity,
            "market_value": item.market_value,
            "weight": item.weight,
        }
        for item in rows
    ]


@router.get("/{portfolio_id}/trades")
def get_trades(portfolio_id: int, db: Session = Depends(get_db)) -> list[dict]:
    rows = db.query(Trade).filter(Trade.portfolio_id == portfolio_id).order_by(Trade.trade_date.desc()).limit(500).all()
    return [
        {
            "trade_date": item.trade_date,
            "instrument_id": item.instrument_id,
            "side": item.side,
            "quantity": item.quantity,
            "price": item.price,
            "net_amount": item.net_amount,
            "status": item.status,
        }
        for item in rows
    ]


@router.get("/{portfolio_id}/cash-flows")
def get_cash_flows(portfolio_id: int, db: Session = Depends(get_db)) -> list[dict]:
    rows = db.query(CashFlow).filter(CashFlow.portfolio_id == portfolio_id).order_by(CashFlow.flow_date.desc()).limit(500).all()
    return [
        {
            "flow_date": item.flow_date,
            "flow_type": item.flow_type,
            "amount": item.amount,
            "available_cash": item.available_cash,
            "position_value": item.position_value,
            "total_asset": item.total_asset,
        }
        for item in rows
    ]

