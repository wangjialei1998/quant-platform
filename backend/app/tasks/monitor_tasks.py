from app.core.database import SessionLocal
from app.models.portfolio import Portfolio
from app.services.demo_backtest_service import DemoBacktestService
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
        result = DemoBacktestService(db).initialize_portfolio(portfolio_id)
        result["run_type"] = run_type
        return result
    finally:
        db.close()
