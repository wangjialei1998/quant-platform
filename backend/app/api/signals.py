from collections import defaultdict
from datetime import date, datetime
from statistics import mean, pstdev
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.engines.signal_insight_engine import SignalInsightEngine
from app.models.instrument import Instrument
from app.models.market_data import MarketDailyBar
from app.models.portfolio import Portfolio, PortfolioInstrument, PortfolioPosition
from app.models.signal import Signal

router = APIRouter()


@router.get("/{portfolio_id}/signals/price-chart")
def price_chart(portfolio_id: int, normalized: bool = True, db: Session = Depends(get_db)) -> dict:
    portfolio = db.get(Portfolio, portfolio_id)
    if not portfolio:
        return {"dates": [], "series": [], "signals": []}
    end_date = _today()
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
            .filter(
                MarketDailyBar.instrument_id == instrument.id,
                MarketDailyBar.trade_date >= portfolio.start_date,
                MarketDailyBar.trade_date <= end_date,
            )
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
        series.append(
            {
                "symbol": instrument.symbol,
                "name": instrument.name,
                "type": "line",
                "data": list(zip(dates, values)),
            }
        )

    signals = (
        db.query(Signal, Instrument)
        .join(Instrument, Signal.instrument_id == Instrument.id)
        .filter(
            Signal.portfolio_id == portfolio_id,
            Signal.signal_date >= portfolio.start_date,
            Signal.signal_date <= end_date,
        )
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
                "name": instrument.name,
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
    signals = (
        db.query(Signal)
        .filter(Signal.portfolio_id == portfolio_id)
        .order_by(Signal.signal_date)
        .all()
    )
    if not signals:
        return SignalInsightEngine().empty_effectiveness()
    bars_by_instrument = _bars_by_instrument(db, [item.instrument_id for item in signals])
    return {
        "buy": _effectiveness_for_side([item for item in signals if item.side == "buy"], bars_by_instrument, "buy"),
        "sell": _effectiveness_for_side([item for item in signals if item.side == "sell"], bars_by_instrument, "sell"),
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
    signals = (
        db.query(Signal)
        .filter(Signal.portfolio_id == portfolio_id)
        .order_by(Signal.signal_date)
        .all()
    )
    if not signals:
        return {
            "summary": "暂无交易信号。",
            "buy": "买入信号 0 次，间隔: -",
            "sell": "卖出信号 0 次，间隔: -",
        }
    intervals = [
        (signals[index].signal_date - signals[index - 1].signal_date).days
        for index in range(1, len(signals))
    ]
    buy_signals = [item for item in signals if item.side == "buy"]
    sell_signals = [item for item in signals if item.side == "sell"]
    avg_interval = round(sum(intervals) / len(intervals), 1) if intervals else 0
    return {
        "summary": f"{len(signals)} 次信号，平均间隔 {avg_interval} 天。",
        "buy": f"买入信号 {len(buy_signals)} 次，间隔: {_avg_signal_interval(buy_signals)} 天",
        "sell": f"卖出信号 {len(sell_signals)} 次，间隔: {_avg_signal_interval(sell_signals)} 天",
    }


@router.get("/{portfolio_id}/signals/risks")
def risks(portfolio_id: int, db: Session = Depends(get_db)) -> list[dict]:
    signals = (
        db.query(Signal)
        .filter(Signal.portfolio_id == portfolio_id)
        .order_by(Signal.signal_date)
        .all()
    )
    risks_list = []
    if not signals:
        return risks_list

    max_30_day_signals = _max_rolling_signal_count(signals, 30)
    if max_30_day_signals > 13:
        risks_list.append(
            {
                "type": "frequent_trading",
                "level": "high",
                "message": f"30天内最多出现 {max_30_day_signals} 次信号，交易频率偏高。",
            }
        )

    bars_by_instrument = _bars_by_instrument(db, [item.instrument_id for item in signals])
    instruments = {
        item.id: item
        for item in db.query(Instrument)
        .filter(Instrument.id.in_(list(bars_by_instrument.keys()) or [0]))
        .all()
    }
    buy_signals = [item for item in signals if item.side == "buy"]
    failed_buys = [
        item
        for item in buy_signals
        if (_forward_return(item, bars_by_instrument, 5) or 0) < -0.02
    ]
    if buy_signals and len(failed_buys) / len(buy_signals) >= 0.3:
        risks_list.append(
            {
                "type": "post_buy_drop",
                "level": "high",
                "message": f"{len(failed_buys)} 次买入后5日跌幅超过2%，买入信号短期承压。",
            }
        )

    switch_count = _short_switch_count(signals)
    if switch_count:
        risks_list.append(
            {
                "type": "signal_switch",
                "level": "warning",
                "message": f"发现 {switch_count} 次20天内 B-S-B 短期切换，信号可能偏噪声。",
            }
        )

    max_empty_days = _max_empty_position_days(db, portfolio_id)
    if max_empty_days >= 60:
        risks_list.append(
            {
                "type": "long_empty_position",
                "level": "warning",
                "message": f"最长连续空仓 {max_empty_days} 天，资金利用率需要关注。",
            }
        )

    high_volatility_names = _high_volatility_names(bars_by_instrument, instruments)
    if high_volatility_names:
        risks_list.append(
            {
                "type": "high_volatility",
                "level": "warning",
                "message": f"{'、'.join(high_volatility_names)} 年化波动率超过45%，标的波动偏高。",
            }
        )
    return risks_list


@router.get("/{portfolio_id}/signals/volatility")
def volatility(portfolio_id: int, db: Session = Depends(get_db)) -> dict:
    portfolio = db.get(Portfolio, portfolio_id)
    if not portfolio:
        return {"months": [], "series": []}
    end_date = _today()
    instruments = (
        db.query(Instrument)
        .join(PortfolioInstrument, PortfolioInstrument.instrument_id == Instrument.id)
        .filter(PortfolioInstrument.portfolio_id == portfolio_id)
        .all()
    )
    months: set[str] = set()
    grouped: dict[int, dict[str, object]] = {}
    for instrument in instruments:
        bars = (
            db.query(MarketDailyBar)
            .filter(
                MarketDailyBar.instrument_id == instrument.id,
                MarketDailyBar.trade_date >= portfolio.start_date,
                MarketDailyBar.trade_date <= end_date,
            )
            .order_by(MarketDailyBar.trade_date)
            .all()
        )
        previous = None
        for bar in bars:
            month = bar.trade_date.strftime("%Y-%m")
            months.add(month)
            close = float(bar.close)
            if previous:
                item = grouped.setdefault(
                    instrument.id,
                    {"symbol": instrument.symbol, "name": instrument.name, "returns": defaultdict(list)},
                )
                returns = item["returns"]
                if isinstance(returns, defaultdict):
                    returns[month].append(close / previous - 1)
            previous = close
    ordered_months = sorted(months)
    return {
        "months": ordered_months,
        "series": [
            {
                "symbol": item["symbol"],
                "name": item["name"],
                "data": [
                    round(pstdev(returns[month]), 6) if len(returns[month]) > 1 else 0
                    for month in ordered_months
                ],
            }
            for item in sorted(grouped.values(), key=lambda value: str(value["symbol"]))
            for returns in [item["returns"]]
            if isinstance(returns, defaultdict)
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


def _bars_by_instrument(db: Session, instrument_ids: list[int]) -> dict[int, list[MarketDailyBar]]:
    rows = (
        db.query(MarketDailyBar)
        .filter(MarketDailyBar.instrument_id.in_(instrument_ids or [0]))
        .order_by(MarketDailyBar.instrument_id, MarketDailyBar.trade_date)
        .all()
    )
    grouped: dict[int, list[MarketDailyBar]] = defaultdict(list)
    for row in rows:
        grouped[row.instrument_id].append(row)
    return grouped


def _today() -> date:
    return datetime.now(ZoneInfo("Asia/Shanghai")).date()


def _effectiveness_for_side(signals: list[Signal], bars_by_instrument: dict[int, list[MarketDailyBar]], side: str) -> dict:
    returns_5 = [_forward_return(item, bars_by_instrument, 5) for item in signals]
    returns_20 = [_forward_return(item, bars_by_instrument, 20) for item in signals]
    returns_5 = [item for item in returns_5 if item is not None]
    returns_20 = [item for item in returns_20 if item is not None]
    all_returns = returns_5 + returns_20
    return {
        "count": len(signals),
        "day_5": _success_rate(returns_5, side),
        "day_20": _success_rate(returns_20, side),
        "avg_return": round(mean(all_returns) * 100, 2) if all_returns else 0,
    }


def _forward_return(signal: Signal, bars_by_instrument: dict[int, list[MarketDailyBar]], horizon: int) -> float | None:
    bars = bars_by_instrument.get(signal.instrument_id, [])
    index = next((idx for idx, row in enumerate(bars) if row.trade_date >= signal.signal_date), -1)
    if index < 0 or index + horizon >= len(bars):
        return None
    base_price = float(signal.price or bars[index].close)
    if not base_price:
        return None
    future_price = float(bars[index + horizon].close)
    return future_price / base_price - 1


def _success_rate(returns: list[float], side: str) -> float:
    if not returns:
        return 0
    successes = [item for item in returns if (item > 0 if side == "buy" else item < 0)]
    return round(len(successes) / len(returns) * 100, 1)


def _avg_signal_interval(signals: list[Signal]) -> str:
    if len(signals) < 2:
        return "-"
    intervals = [
        (signals[index].signal_date - signals[index - 1].signal_date).days
        for index in range(1, len(signals))
    ]
    return f"{round(sum(intervals) / len(intervals), 1)}"


def _max_rolling_signal_count(signals: list[Signal], window_days: int) -> int:
    max_count = 0
    start = 0
    for end, signal in enumerate(signals):
        while (signal.signal_date - signals[start].signal_date).days > window_days:
            start += 1
        max_count = max(max_count, end - start + 1)
    return max_count


def _short_switch_count(signals: list[Signal]) -> int:
    count = 0
    ordered = sorted(signals, key=lambda item: item.signal_date)
    for index in range(2, len(ordered)):
        first, middle, last = ordered[index - 2], ordered[index - 1], ordered[index]
        if [first.side, middle.side, last.side] == ["buy", "sell", "buy"]:
            if (last.signal_date - first.signal_date).days <= 20:
                count += 1
    return count


def _max_empty_position_days(db: Session, portfolio_id: int) -> int:
    rows = (
        db.query(PortfolioPosition.trade_date, PortfolioPosition.quantity)
        .filter(PortfolioPosition.portfolio_id == portfolio_id)
        .order_by(PortfolioPosition.trade_date)
        .all()
    )
    if not rows:
        return 0
    by_date: dict = {}
    for trade_date, quantity in rows:
        by_date[trade_date] = by_date.get(trade_date, False) or quantity > 0
    max_empty = 0
    current = 0
    previous_date = None
    for trade_date, holding in sorted(by_date.items()):
        if previous_date is not None and (trade_date - previous_date).days > 1 and not holding:
            current += (trade_date - previous_date).days - 1
        if holding:
            current = 0
        else:
            current += 1
            max_empty = max(max_empty, current)
        previous_date = trade_date
    return max_empty


def _high_volatility_names(bars_by_instrument: dict[int, list[MarketDailyBar]], instruments: dict[int, Instrument]) -> list[str]:
    names = []
    for bars in bars_by_instrument.values():
        returns = []
        previous = None
        for bar in bars:
            close = float(bar.close)
            if previous:
                returns.append(close / previous - 1)
            previous = close
        if len(returns) > 1 and pstdev(returns) * (252**0.5) > 0.45:
            instrument = instruments.get(bars[0].instrument_id)
            names.append(instrument.name if instrument else str(bars[0].instrument_id))
    return names
