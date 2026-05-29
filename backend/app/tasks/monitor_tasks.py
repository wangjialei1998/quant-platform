from app.core.database import SessionLocal
from app.models.portfolio import Portfolio
from app.services.backtest_execution_service import BacktestExecutionService
from app.tasks.chart_tasks import build_chart_snapshots
from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.monitor_tasks.monitor_all_portfolios")
def monitor_all_portfolios() -> dict:
    db = SessionLocal()
    try:
        portfolios = db.query(Portfolio).filter(Portfolio.status == "running").all()
        task_ids = [monitor_portfolio.delay(item.id, "scheduled_monitor").id for item in portfolios]
        return {"status": "submitted", "task_ids": task_ids}
    finally:
        db.close()


@celery_app.task(name="app.tasks.monitor_tasks.monitor_portfolio")
def monitor_portfolio(portfolio_id: int, run_type: str = "manual_monitor") -> dict:
    db = SessionLocal()
    try:
        result = BacktestExecutionService(db).initialize_portfolio(portfolio_id, run_type)
        result["run_type"] = run_type
        if result.get("status") == "success":
            build_chart_snapshots.delay(portfolio_id)
        return result
    finally:
        db.close()
