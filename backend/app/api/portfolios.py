from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.metric import PortfolioMetric
from app.models.instrument import Instrument
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
    try:
        PortfolioService(db).delete(portfolio_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
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
        annual_return=metric.annual_return if metric else 0.0,
        win_rate=metric.win_rate if metric else 0.0,
        profit_loss_ratio=metric.profit_loss_ratio if metric else 0.0,
        sharpe_ratio=metric.sharpe_ratio if metric else 0.0,
        current_drawdown=metric.current_drawdown if metric else 0.0,
        total_return=metric.total_return if metric else 0.0,
        max_drawdown=metric.max_drawdown if metric else 0.0,
        max_drawdown_days=metric.max_drawdown_days if metric else 0,
        volatility=metric.volatility if metric else 0.0,
        sqn=metric.sqn if metric else 0.0,
        vwr=metric.vwr if metric else 0.0,
        trade_count=metric.trade_count if metric else 0,
        running_days=metric.running_days if metric else 0,
        start_date=portfolio.start_date,
        updated_at=portfolio.updated_at,
        email_enabled=portfolio.email_enabled,
        last_run_at=portfolio.last_run_at,
    )


@router.get("/{portfolio_id}/metrics")
def get_portfolio_metrics(portfolio_id: int, db: Session = Depends(get_db)) -> list[dict]:
    rows = (
        db.query(PortfolioMetric)
        .filter(PortfolioMetric.portfolio_id == portfolio_id)
        .order_by(PortfolioMetric.metric_date)
        .all()
    )
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
def get_equity_curve(portfolio_id: int, db: Session = Depends(get_db)) -> dict:
    rows = (
        db.query(PortfolioMetric)
        .filter(PortfolioMetric.portfolio_id == portfolio_id)
        .order_by(PortfolioMetric.metric_date)
        .all()
    )
    trades = (
        db.query(Trade, Instrument)
        .join(Instrument, Trade.instrument_id == Instrument.id)
        .filter(Trade.portfolio_id == portfolio_id, Trade.status == "filled")
        .order_by(Trade.trade_date)
        .all()
    )
    return {
        "dates": [item.metric_date.isoformat() for item in rows],
        "portfolio": [round(item.net_value, 6) for item in rows],
        "benchmark": [],
        "trades": [
            {
                "date": trade.trade_date.isoformat(),
                "side": trade.side,
                "symbol": instrument.symbol,
                "net_value": _metric_value_on(rows, trade.trade_date),
            }
            for trade, instrument in trades
        ],
    }


@router.get("/{portfolio_id}/drawdown")
def get_drawdown(portfolio_id: int, db: Session = Depends(get_db)) -> dict:
    rows = (
        db.query(PortfolioMetric)
        .filter(PortfolioMetric.portfolio_id == portfolio_id)
        .order_by(PortfolioMetric.metric_date)
        .all()
    )
    return {
        "dates": [item.metric_date.isoformat() for item in rows],
        "drawdown": [round(item.current_drawdown, 6) for item in rows],
    }


@router.get("/{portfolio_id}/positions")
def get_positions(portfolio_id: int, db: Session = Depends(get_db)) -> list[dict]:
    rows = db.query(PortfolioPosition).filter(PortfolioPosition.portfolio_id == portfolio_id).limit(500).all()
    instruments = {
        item.id: item
        for item in db.query(Instrument)
        .filter(Instrument.id.in_([row.instrument_id for row in rows] or [0]))
        .all()
    }
    return [
        {
            "date": item.trade_date,
            "instrument_id": item.instrument_id,
            "symbol": instruments[item.instrument_id].symbol if item.instrument_id in instruments else item.instrument_id,
            "quantity": item.quantity,
            "market_value": item.market_value,
            "weight": item.weight,
        }
        for item in rows
    ]


@router.get("/{portfolio_id}/trades")
def get_trades(portfolio_id: int, db: Session = Depends(get_db)) -> list[dict]:
    rows = db.query(Trade).filter(Trade.portfolio_id == portfolio_id).order_by(Trade.trade_date.desc()).limit(500).all()
    instruments = {
        item.id: item
        for item in db.query(Instrument)
        .filter(Instrument.id.in_([row.instrument_id for row in rows] or [0]))
        .all()
    }
    return [
        {
            "trade_date": item.trade_date,
            "instrument_id": item.instrument_id,
            "symbol": instruments[item.instrument_id].symbol if item.instrument_id in instruments else item.instrument_id,
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
    rows = (
        db.query(CashFlow)
        .filter(CashFlow.portfolio_id == portfolio_id, CashFlow.flow_type.in_(["buy", "sell"]))
        .order_by(CashFlow.flow_date.desc())
        .limit(500)
        .all()
    )
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


@router.patch("/{portfolio_id}/email")
def update_email_enabled(portfolio_id: int, email_enabled: bool, db: Session = Depends(get_db)) -> dict:
    portfolio = db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    portfolio.email_enabled = email_enabled
    db.commit()
    return {"message": "ok", "email_enabled": portfolio.email_enabled}


def _metric_value_on(rows: list[PortfolioMetric], trade_date) -> float | None:
    for row in rows:
        if row.metric_date == trade_date:
            return round(row.net_value, 6)
    return None
