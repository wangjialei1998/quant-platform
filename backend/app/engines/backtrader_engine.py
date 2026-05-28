from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class BacktestResult:
    start_date: date
    end_date: date
    trades: list[dict]
    signals: list[dict]
    equity_curve: list[dict]


class BacktraderEngine:
    def run_daily_backtest(self, start_date: date, end_date: date) -> BacktestResult:
        return BacktestResult(
            start_date=start_date,
            end_date=end_date,
            trades=[],
            signals=[],
            equity_curve=[],
        )

