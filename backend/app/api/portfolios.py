from bisect import bisect_right
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.instrument import Instrument
from app.models.market_data import MarketDailyBar
from app.models.metric import PortfolioMetric
from app.models.portfolio import Portfolio, PortfolioInstrument, PortfolioPosition
from app.models.strategy import Strategy
from app.models.trade import CashFlow, Trade
from app.schemas.common import MessageResponse, TaskResponse
from app.schemas.instrument import InstrumentCreate
from app.schemas.portfolio import PortfolioCreate, PortfolioListItem, PortfolioRead, PortfolioSummary, PortfolioUpdate
from app.services.instrument_service import InstrumentService
from app.services.market_data_service import MarketDataService
from app.services.portfolio_service import PortfolioService
from app.tasks.backtest_tasks import initialize_portfolio
from app.tasks.monitor_tasks import monitor_portfolio
from app.utils.errors import NotFoundError, ValidationError

router = APIRouter()


@router.get("", response_model=list[PortfolioListItem])
def list_portfolios(db: Session = Depends(get_db)) -> list[PortfolioListItem]:
    portfolios = db.query(Portfolio).order_by(Portfolio.created_at.desc()).all()
    if not portfolios:
        return []

    portfolio_ids = [item.id for item in portfolios]
    strategy_names = dict(db.query(Strategy.id, Strategy.name).all())
    instrument_counts = dict(
        db.query(PortfolioInstrument.portfolio_id, func.count(PortfolioInstrument.id))
        .filter(PortfolioInstrument.portfolio_id.in_(portfolio_ids))
        .group_by(PortfolioInstrument.portfolio_id)
        .all()
    )
    latest_dates = dict(
        db.query(PortfolioMetric.portfolio_id, func.max(PortfolioMetric.metric_date))
        .filter(PortfolioMetric.portfolio_id.in_(portfolio_ids))
        .group_by(PortfolioMetric.portfolio_id)
        .all()
    )
    latest_metrics = {}
    latest_date_values = [item for item in latest_dates.values() if item is not None]
    if latest_date_values:
        metric_rows = (
            db.query(PortfolioMetric)
            .filter(
                PortfolioMetric.portfolio_id.in_(portfolio_ids),
                PortfolioMetric.metric_date.in_(latest_date_values),
            )
            .all()
        )
        latest_metrics = {
            item.portfolio_id: item
            for item in metric_rows
            if latest_dates.get(item.portfolio_id) == item.metric_date
        }

    return [
        _portfolio_list_item(
            portfolio,
            strategy_name=strategy_names.get(portfolio.strategy_id) or f"策略 {portfolio.strategy_id}",
            instrument_count=int(instrument_counts.get(portfolio.id, 0)),
            metric=latest_metrics.get(portfolio.id),
        )
        for portfolio in portfolios
    ]


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


@router.get("/{portfolio_id}/edit")
def get_portfolio_edit(portfolio_id: int, db: Session = Depends(get_db)) -> dict:
    portfolio = db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    instrument_ids = [
        row.instrument_id
        for row in db.query(PortfolioInstrument.instrument_id)
        .filter(PortfolioInstrument.portfolio_id == portfolio_id)
        .order_by(PortfolioInstrument.instrument_id)
        .all()
    ]
    return {
        "id": portfolio.id,
        "name": portfolio.name,
        "strategy_id": portfolio.strategy_id,
        "instrument_ids": instrument_ids,
        "initial_cash": portfolio.initial_cash,
        "start_date": portfolio.start_date,
        "email_enabled": portfolio.email_enabled,
        "commission_rate": portfolio.commission_rate,
        "stamp_tax_rate": portfolio.stamp_tax_rate,
        "slippage_rate": portfolio.slippage_rate,
        "status": portfolio.status,
    }


@router.patch("/{portfolio_id}", response_model=TaskResponse)
def update_portfolio(portfolio_id: int, payload: PortfolioUpdate, db: Session = Depends(get_db)) -> TaskResponse:
    try:
        portfolio = PortfolioService(db).update(portfolio_id, payload)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    task = initialize_portfolio.delay(portfolio.id)
    return TaskResponse(task_id=task.id)


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
def get_equity_curve(portfolio_id: int, benchmark_symbol: str | None = None, db: Session = Depends(get_db)) -> dict:
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
    benchmark = _benchmark_curve(db, rows, benchmark_symbol)
    return {
        "dates": [item.metric_date.isoformat() for item in rows],
        "portfolio": [round(item.net_value, 6) for item in rows],
        "benchmark": benchmark,
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


@router.get("/{portfolio_id}/performance")
def get_period_performance(portfolio_id: int, db: Session = Depends(get_db)) -> dict:
    rows = (
        db.query(PortfolioMetric)
        .filter(PortfolioMetric.portfolio_id == portfolio_id)
        .order_by(PortfolioMetric.metric_date)
        .all()
    )
    monthly = _period_returns(rows, "%Y-%m")
    yearly = _period_returns(rows, "%Y")
    return {"monthly": monthly, "yearly": yearly}


@router.get("/{portfolio_id}/position-values")
def get_position_values(portfolio_id: int, db: Session = Depends(get_db)) -> dict:
    rows = (
        db.query(PortfolioPosition, Instrument)
        .join(Instrument, PortfolioPosition.instrument_id == Instrument.id)
        .filter(PortfolioPosition.portfolio_id == portfolio_id)
        .order_by(PortfolioPosition.trade_date.desc(), Instrument.symbol)
        .limit(2000)
        .all()
    )
    dates = sorted({position.trade_date.isoformat() for position, _ in rows})
    grouped: dict[str, dict[str, float]] = {}
    for position, instrument in rows:
        grouped.setdefault(instrument.symbol, {})[position.trade_date.isoformat()] = float(position.market_value)
    return {
        "dates": dates,
        "series": [
            {
                "name": symbol,
                "data": [round(values.get(day, 0), 2) for day in dates],
            }
            for symbol, values in sorted(grouped.items())
        ],
    }


@router.get("/{portfolio_id}/return-contribution")
def get_return_contribution(portfolio_id: int, period: str = "month", db: Session = Depends(get_db)) -> dict:
    if period not in {"month", "year"}:
        raise HTTPException(status_code=400, detail="period must be month or year")
    portfolio = db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    instruments = (
        db.query(Instrument)
        .join(PortfolioInstrument, PortfolioInstrument.instrument_id == Instrument.id)
        .filter(PortfolioInstrument.portfolio_id == portfolio_id)
        .order_by(Instrument.symbol)
        .all()
    )
    metrics = (
        db.query(PortfolioMetric)
        .filter(PortfolioMetric.portfolio_id == portfolio_id)
        .order_by(PortfolioMetric.metric_date)
        .all()
    )
    if not instruments or not metrics:
        return {"period": period, "periods": [], "symbols": [], "series": []}

    period_format = "%Y" if period == "year" else "%Y-%m"
    metric_groups: dict[str, list[PortfolioMetric]] = {}
    for metric in metrics:
        metric_groups.setdefault(metric.metric_date.strftime(period_format), []).append(metric)

    position_rows = (
        db.query(PortfolioPosition)
        .filter(PortfolioPosition.portfolio_id == portfolio_id)
        .order_by(PortfolioPosition.instrument_id, PortfolioPosition.trade_date)
        .all()
    )
    position_values: dict[int, list[tuple[date, Decimal]]] = {instrument.id: [] for instrument in instruments}
    for position in position_rows:
        position_values.setdefault(position.instrument_id, []).append((position.trade_date, position.market_value))
    position_dates = {
        instrument_id: [item[0] for item in values]
        for instrument_id, values in position_values.items()
    }

    trade_rows = (
        db.query(Trade)
        .filter(Trade.portfolio_id == portfolio_id, Trade.status == "filled")
        .order_by(Trade.trade_date)
        .all()
    )
    trade_amounts: dict[tuple[str, int], dict[str, Decimal]] = {}
    for trade in trade_rows:
        key = (trade.trade_date.strftime(period_format), trade.instrument_id)
        amounts = trade_amounts.setdefault(key, {"buy": Decimal("0"), "sell": Decimal("0")})
        if trade.side == "buy":
            amounts["buy"] += trade.net_amount
        elif trade.side == "sell":
            amounts["sell"] += trade.net_amount

    periods = sorted(metric_groups)
    series = [{"symbol": instrument.symbol, "data": []} for instrument in instruments]
    previous_metric: PortfolioMetric | None = None

    for period_key in periods:
        group = metric_groups[period_key]
        end_metric = group[-1]
        start_asset = (
            portfolio.initial_cash * Decimal(str(previous_metric.net_value))
            if previous_metric
            else portfolio.initial_cash
        )
        start_date = previous_metric.metric_date if previous_metric else None
        end_date = end_metric.metric_date

        for index, instrument in enumerate(instruments):
            values = position_values.get(instrument.id, [])
            dates = position_dates.get(instrument.id, [])
            start_value = _position_value_on(values, dates, start_date)
            end_value = _position_value_on(values, dates, end_date)
            amounts = trade_amounts.get((period_key, instrument.id), {"buy": Decimal("0"), "sell": Decimal("0")})
            profit = end_value - start_value - amounts["buy"] + amounts["sell"]
            contribution = profit / start_asset if start_asset > 0 else Decimal("0")
            series[index]["data"].append(round(float(contribution), 6))

        previous_metric = end_metric

    return {
        "period": period,
        "periods": periods,
        "symbols": [instrument.symbol for instrument in instruments],
        "series": series,
    }


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


def _period_returns(rows: list[PortfolioMetric], period_format: str) -> list[dict]:
    if not rows:
        return []
    grouped: dict[str, list[PortfolioMetric]] = {}
    for row in rows:
        grouped.setdefault(row.metric_date.strftime(period_format), []).append(row)
    result = []
    previous_end_value = 1.0
    for period, values in sorted(grouped.items()):
        start_value = previous_end_value
        end_value = values[-1].net_value
        result.append(
            {
                "period": period,
                "start_net_value": round(start_value, 6),
                "end_net_value": round(end_value, 6),
                "return": round(end_value / start_value - 1, 6) if start_value else 0,
            }
        )
        previous_end_value = end_value
    return result


def _position_value_on(
    values: list[tuple[date, Decimal]],
    dates: list[date],
    target_date: date | None,
) -> Decimal:
    if target_date is None or not values:
        return Decimal("0")
    index = bisect_right(dates, target_date) - 1
    if index < 0:
        return Decimal("0")
    return values[index][1]


def _portfolio_list_item(
    portfolio: Portfolio,
    strategy_name: str | None,
    instrument_count: int,
    metric: PortfolioMetric | None,
) -> PortfolioListItem:
    latest_net_value = metric.net_value if metric else 1.0
    current_total_asset = (portfolio.initial_cash * Decimal(str(latest_net_value))).quantize(Decimal("0.01"))
    return PortfolioListItem(
        id=portfolio.id,
        name=portfolio.name,
        strategy_id=portfolio.strategy_id,
        initial_cash=portfolio.initial_cash,
        start_date=portfolio.start_date,
        status=portfolio.status,
        email_enabled=portfolio.email_enabled,
        commission_rate=portfolio.commission_rate,
        stamp_tax_rate=portfolio.stamp_tax_rate,
        slippage_rate=portfolio.slippage_rate,
        last_run_at=portfolio.last_run_at,
        created_at=portfolio.created_at,
        updated_at=portfolio.updated_at,
        strategy_name=strategy_name,
        instrument_count=instrument_count,
        latest_net_value=latest_net_value,
        current_total_asset=current_total_asset,
        total_return=metric.total_return if metric else 0.0,
        max_drawdown=metric.max_drawdown if metric else 0.0,
        latest_metric_date=metric.metric_date if metric else None,
    )


def _benchmark_curve(db: Session, rows: list[PortfolioMetric], benchmark_symbol: str | None) -> list[float | None]:
    if not rows or not benchmark_symbol:
        return []

    start_date: date = rows[0].metric_date
    end_date: date = rows[-1].metric_date
    normalized_symbol = "000300.SH" if benchmark_symbol in {"沪深300", "HS300", "CSI300"} else benchmark_symbol
    try:
        instrument = InstrumentService(db).create(
            InstrumentCreate(
                symbol=normalized_symbol,
                name="沪深300" if normalized_symbol in {"000300", "000300.SH"} else None,
                instrument_type="index",
                exchange="SSE",
            )
        )
        MarketDataService(db).ensure_daily_bars([instrument], start_date, end_date)
        db.commit()
    except Exception:
        db.rollback()
        instrument = (
            db.query(Instrument)
            .filter(Instrument.symbol.in_([normalized_symbol, "000300.SH"]))
            .first()
        )
        if not instrument:
            return [None for _ in rows]

    bars = (
        db.query(MarketDailyBar)
        .filter(
            MarketDailyBar.instrument_id == instrument.id,
            MarketDailyBar.trade_date >= start_date,
            MarketDailyBar.trade_date <= end_date,
            MarketDailyBar.adjustment_type == "none",
        )
        .order_by(MarketDailyBar.trade_date)
        .all()
    )
    if not bars:
        return [None for _ in rows]

    bar_by_date = {bar.trade_date: float(bar.close) for bar in bars}
    first_close: float | None = None
    last_close: float | None = None
    curve: list[float | None] = []
    for row in rows:
        close = bar_by_date.get(row.metric_date)
        if close is not None:
            last_close = close
            if first_close is None:
                first_close = close
        if first_close and last_close:
            curve.append(round(last_close / first_close, 6))
        else:
            curve.append(None)
    return curve
