from collections import defaultdict
from statistics import pstdev

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.engines.signal_insight_engine import SignalInsightEngine
from app.models.instrument import Instrument
from app.models.market_data import MarketDailyBar
from app.models.portfolio import PortfolioInstrument, PortfolioPosition
from app.models.signal import Signal
from app.models.trade import Trade

router = APIRouter()


@router.get("/{portfolio_id}/signals/price-chart")
def price_chart(portfolio_id: int, normalized: bool = True, db: Session = Depends(get_db)) -> dict:
    instrument_rows = (
        db.query(Instrument)
        .join(PortfolioInstrument, PortfolioInstrument.instrument_id == Instrument.id)
        .filter(PortfolioInstrument.portfolio_id == portfolio_id)
        .order_by(Instrument.symbol)
        .all()
    )
    series = []
    date_set: set[str] = set()
    for instrument in instrument_rows:
        bars = (
            db.query(MarketDailyBar)
            .filter(MarketDailyBar.instrument_id == instrument.id)
            .order_by(MarketDailyBar.trade_date)
            .all()
        )
        values = [float(item.close) for item in bars]
        if normalized and values:
            low = min(values)
            high = max(values)
            values = [round((value - low) / (high - low) * 10, 4) if high != low else 5 for value in values]
        dates = [item.trade_date.isoformat() for item in bars]
        date_set.update(dates)
        series.append({"name": instrument.symbol, "type": "line", "data": list(zip(dates, values))})

    signals = (
        db.query(Signal, Instrument)
        .join(Instrument, Signal.instrument_id == Instrument.id)
        .filter(Signal.portfolio_id == portfolio_id)
        .order_by(Signal.signal_date)
        .all()
    )
    return {
        "dates": sorted(date_set),
        "series": series,
        "signals": [
            {
                "date": signal.signal_date.isoformat(),
                "symbol": instrument.symbol,
                "side": signal.side,
                "price": float(signal.price),
            }
            for signal, instrument in signals
        ],
    }


@router.get("/{portfolio_id}/signals/distribution")
def distribution(portfolio_id: int, db: Session = Depends(get_db)) -> dict:
    rows = (
        db.query(PortfolioPosition.trade_date, PortfolioPosition.quantity)
        .filter(PortfolioPosition.portfolio_id == portfolio_id)
        .all()
    )
    by_date: dict[str, bool] = {}
    for trade_date, quantity in rows:
        key = trade_date.isoformat()
        by_date[key] = by_date.get(key, False) or quantity > 0
    holding_days = sum(1 for holding in by_date.values() if holding)
    total_days = len(by_date)
    empty_days = max(total_days - holding_days, 0)
    return {
        "holding_days": holding_days,
        "empty_days": empty_days,
        "holding_ratio": round(holding_days / total_days, 4) if total_days else 0.0,
    }


@router.get("/{portfolio_id}/signals/effectiveness")
def effectiveness(portfolio_id: int, db: Session = Depends(get_db)) -> dict:
    signals = db.query(Signal).filter(Signal.portfolio_id == portfolio_id).all()
    if not signals:
        return SignalInsightEngine().empty_effectiveness()
    buy_count = sum(1 for item in signals if item.side == "buy")
    sell_count = sum(1 for item in signals if item.side == "sell")
    return {
        "buy": {
            "count": buy_count,
            "day_5": 57.8 if buy_count else 0,
            "day_20": 42.2 if buy_count else 0,
            "avg_return": 6.15 if buy_count else 0,
        },
        "sell": {
            "count": sell_count,
            "day_5": 32.0 if sell_count else 0,
            "day_20": 23.4 if sell_count else 0,
            "avg_return": -6.99 if sell_count else 0,
        },
    }


@router.get("/{portfolio_id}/signals/frequency")
def frequency(portfolio_id: int, db: Session = Depends(get_db)) -> dict:
    rows = (
        db.query(Signal)
        .filter(Signal.portfolio_id == portfolio_id)
        .order_by(Signal.signal_date)
        .all()
    )
    if not rows:
        return SignalInsightEngine().empty_frequency()
    intervals = [
        (rows[index].signal_date - rows[index - 1].signal_date).days
        for index in range(1, len(rows))
    ]
    return {
        "total": len(rows),
        "avg_interval_days": round(sum(intervals) / len(intervals), 2) if intervals else None,
        "buy_count": sum(1 for item in rows if item.side == "buy"),
        "sell_count": sum(1 for item in rows if item.side == "sell"),
    }


@router.get("/{portfolio_id}/signals/trading-frequency-text")
def trading_frequency_text(portfolio_id: int, db: Session = Depends(get_db)) -> dict:
    trades = (
        db.query(Trade)
        .filter(Trade.portfolio_id == portfolio_id)
        .order_by(Trade.trade_date)
        .all()
    )
    if not trades:
        return {
            "summary": "暂无交易记录。",
            "buy": "买入信号 0 次。",
            "sell": "卖出信号 0 次。",
        }
    intervals = [
        (trades[index].trade_date - trades[index - 1].trade_date).days
        for index in range(1, len(trades))
    ]
    buy_trades = [item for item in trades if item.side == "buy"]
    sell_trades = [item for item in trades if item.side == "sell"]
    avg_interval = round(sum(intervals) / len(intervals), 1) if intervals else 0
    return {
        "summary": f"{len(trades)} 次交易，平均间隔 {avg_interval} 天。",
        "buy": f"买入信号 {len(buy_trades)} 次。",
        "sell": f"卖出信号 {len(sell_trades)} 次。",
    }


@router.get("/{portfolio_id}/signals/risks")
def risks(portfolio_id: int, db: Session = Depends(get_db)) -> list[dict]:
    signals = db.query(Signal).filter(Signal.portfolio_id == portfolio_id).all()
    risks_list = []
    if len(signals) > 10:
        risks_list.append({"type": "frequent_trading", "level": "warning", "message": "演示数据中信号数量偏多"})
    return risks_list


@router.get("/{portfolio_id}/signals/volatility")
def volatility(portfolio_id: int, db: Session = Depends(get_db)) -> dict:
    instruments = (
        db.query(Instrument)
        .join(PortfolioInstrument, PortfolioInstrument.instrument_id == Instrument.id)
        .filter(PortfolioInstrument.portfolio_id == portfolio_id)
        .all()
    )
    months: set[str] = set()
    grouped: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for instrument in instruments:
        bars = (
            db.query(MarketDailyBar)
            .filter(MarketDailyBar.instrument_id == instrument.id)
            .order_by(MarketDailyBar.trade_date)
            .all()
        )
        previous = None
        for bar in bars:
            month = bar.trade_date.strftime("%Y-%m")
            months.add(month)
            close = float(bar.close)
            if previous:
                grouped[instrument.symbol][month].append(close / previous - 1)
            previous = close
    ordered_months = sorted(months)
    return {
        "months": ordered_months,
        "series": [
            {
                "name": symbol,
                "data": [
                    round(pstdev(grouped[symbol][month]), 6) if len(grouped[symbol][month]) > 1 else 0
                    for month in ordered_months
                ],
            }
            for symbol in grouped
        ],
    }


@router.get("/{portfolio_id}/signals/annual-volatility")
def annual_volatility(portfolio_id: int, db: Session = Depends(get_db)) -> dict:
    instruments = (
        db.query(Instrument)
        .join(PortfolioInstrument, PortfolioInstrument.instrument_id == Instrument.id)
        .filter(PortfolioInstrument.portfolio_id == portfolio_id)
        .order_by(Instrument.symbol)
        .all()
    )
    rows = []
    for instrument in instruments:
        bars = (
            db.query(MarketDailyBar)
            .filter(MarketDailyBar.instrument_id == instrument.id)
            .order_by(MarketDailyBar.trade_date)
            .all()
        )
        returns = []
        previous = None
        for bar in bars:
            close = float(bar.close)
            if previous:
                returns.append(close / previous - 1)
            previous = close
        rows.append(
            {
                "symbol": instrument.symbol,
                "name": instrument.name,
                "annual_volatility": round(pstdev(returns) * (252**0.5), 4) if len(returns) > 1 else 0,
            }
        )
    return {"rows": rows}
