from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.chart import ChartSnapshot
from app.models.instrument import Instrument
from app.models.metric import PortfolioMetric
from app.models.portfolio import PortfolioPosition
from app.models.signal import Signal
from app.models.trade import Trade
from app.utils.time import utc_now


class ChartService:
    def __init__(self, db: Session):
        self.db = db

    def empty_series(self) -> dict:
        return {"dates": [], "series": []}

    def build_portfolio_snapshots(self, portfolio_id: int) -> dict:
        metrics = (
            self.db.query(PortfolioMetric)
            .filter(PortfolioMetric.portfolio_id == portfolio_id)
            .order_by(PortfolioMetric.metric_date)
            .all()
        )
        trades = (
            self.db.query(Trade, Instrument)
            .join(Instrument, Trade.instrument_id == Instrument.id)
            .filter(Trade.portfolio_id == portfolio_id, Trade.status == "filled")
            .order_by(Trade.trade_date)
            .all()
        )
        signals = (
            self.db.query(Signal, Instrument)
            .join(Instrument, Signal.instrument_id == Instrument.id)
            .filter(Signal.portfolio_id == portfolio_id)
            .order_by(Signal.signal_date)
            .all()
        )
        positions = (
            self.db.query(PortfolioPosition, Instrument)
            .join(Instrument, PortfolioPosition.instrument_id == Instrument.id)
            .filter(PortfolioPosition.portfolio_id == portfolio_id)
            .order_by(PortfolioPosition.trade_date, Instrument.symbol)
            .all()
        )
        position_dates = sorted({position.trade_date.isoformat() for position, _ in positions})
        position_values: dict[str, dict[str, float]] = {}
        for position, instrument in positions:
            position_values.setdefault(instrument.symbol, {})[position.trade_date.isoformat()] = float(position.market_value)

        payloads = {
            "equity_curve": {
                "dates": [item.metric_date.isoformat() for item in metrics],
                "portfolio": [round(item.net_value, 6) for item in metrics],
                "trades": [
                    {
                        "date": trade.trade_date.isoformat(),
                        "side": trade.side,
                        "symbol": instrument.symbol,
                        "net_value": _metric_value_on(metrics, trade.trade_date),
                    }
                    for trade, instrument in trades
                ],
            },
            "drawdown": {
                "dates": [item.metric_date.isoformat() for item in metrics],
                "drawdown": [round(item.current_drawdown, 6) for item in metrics],
            },
            "signals": {
                "signals": [
                    {
                        "date": signal.signal_date.isoformat(),
                        "side": signal.side,
                        "symbol": instrument.symbol,
                        "price": float(signal.price),
                    }
                    for signal, instrument in signals
                ]
            },
            "position_values": {
                "dates": position_dates,
                "series": [
                    {
                        "name": symbol,
                        "data": [round(values.get(day, 0), 2) for day in position_dates],
                    }
                    for symbol, values in sorted(position_values.items())
                ],
            },
            "performance": {
                "monthly": _period_returns(metrics, "%Y-%m"),
                "yearly": _period_returns(metrics, "%Y"),
            },
        }

        self.db.execute(
            delete(ChartSnapshot).where(
                ChartSnapshot.portfolio_id == portfolio_id,
                ChartSnapshot.chart_type.in_(list(payloads)),
            )
        )
        range_start = metrics[0].metric_date if metrics else None
        range_end = metrics[-1].metric_date if metrics else None
        for chart_type, payload in payloads.items():
            self.db.add(
                ChartSnapshot(
                    portfolio_id=portfolio_id,
                    chart_type=chart_type,
                    range_start=range_start,
                    range_end=range_end,
                    payload=payload,
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
            )
        self.db.commit()
        return {
            "status": "success",
            "portfolio_id": portfolio_id,
            "snapshot_count": len(payloads),
            "range_start": range_start.isoformat() if range_start else None,
            "range_end": range_end.isoformat() if range_end else None,
        }


def _metric_value_on(metrics: list[PortfolioMetric], trade_date) -> float | None:
    for metric in metrics:
        if metric.metric_date == trade_date:
            return round(metric.net_value, 6)
    return None


def _period_returns(metrics: list[PortfolioMetric], period_format: str) -> list[dict]:
    if not metrics:
        return []
    grouped: dict[str, list[PortfolioMetric]] = {}
    for metric in metrics:
        grouped.setdefault(metric.metric_date.strftime(period_format), []).append(metric)
    result = []
    previous_end_value = 1.0
    for period, values in sorted(grouped.items()):
        end_value = values[-1].net_value
        result.append(
            {
                "period": period,
                "start_net_value": round(previous_end_value, 6),
                "end_net_value": round(end_value, 6),
                "return": round(end_value / previous_end_value - 1, 6) if previous_end_value else 0,
            }
        )
        previous_end_value = end_value
    return result
