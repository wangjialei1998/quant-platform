from datetime import date

from app.core.database import SessionLocal
from app.models.portfolio import Portfolio
from app.services.backtest_execution_service import BacktestExecutionService
from app.services.market_data_sync_service import MarketDataSyncService
from app.tasks.chart_tasks import build_chart_snapshots
from app.tasks.celery_app import celery_app
from app.utils.trading_calendar import previous_or_same_trading_day


@celery_app.task(name="app.tasks.monitor_tasks.monitor_all_portfolios")
def monitor_all_portfolios(sync_market_data: bool = True) -> dict:
    db = SessionLocal()
    try:
        portfolios = db.query(Portfolio).filter(Portfolio.status == "running").all()
        task_ids = [
            monitor_portfolio.delay(item.id, "scheduled_monitor", sync_market_data).id
            for item in portfolios
        ]
        return {"status": "submitted", "task_ids": task_ids}
    finally:
        db.close()


@celery_app.task(name="app.tasks.monitor_tasks.monitor_portfolio")
def monitor_portfolio(
    portfolio_id: int,
    run_type: str = "manual_monitor",
    sync_market_data: bool = True,
) -> dict:
    db = SessionLocal()
    try:
        result = BacktestExecutionService(db).initialize_portfolio(
            portfolio_id,
            run_type,
            sync_market_data=sync_market_data,
        )
        result["run_type"] = run_type
        if result.get("status") == "success":
            build_chart_snapshots.delay(portfolio_id)
        return result
    finally:
        db.close()


@celery_app.task(name="app.tasks.monitor_tasks.sync_and_monitor_portfolio")
def sync_and_monitor_portfolio(portfolio_id: int, run_type: str = "manual_monitor") -> dict:
    db = SessionLocal()
    try:
        portfolio = db.get(Portfolio, portfolio_id)
        if not portfolio:
            return {"status": "failed", "message": "Portfolio not found", "portfolio_id": portfolio_id}

        end_date = _latest_trading_date(portfolio.start_date)
        sync_result = MarketDataSyncService(db).sync_portfolio_bars(
            portfolio_id,
            end_date,
            retry_on_rate_limit=True,
        )
        result = BacktestExecutionService(db).initialize_portfolio(
            portfolio_id,
            run_type,
            sync_market_data=False,
        )
        result["run_type"] = run_type
        result["market_data_sync"] = sync_result
        if result.get("status") == "success":
            build_chart_snapshots.delay(portfolio_id)
        return result
    finally:
        db.close()


def _latest_trading_date(start_date: date) -> date:
    current = date.today()
    if current < start_date:
        current = start_date
    return previous_or_same_trading_day(current)
