from pathlib import Path

from app.engines.sandbox_runner import SandboxRunner


class BacktraderEngine:
    """Backtrader adapter that executes uploaded strategy code inside Docker sandbox."""

    def run_daily_backtest(self, strategy_path: str, payload: dict) -> dict:
        return SandboxRunner().run_backtest(Path(strategy_path), payload)
