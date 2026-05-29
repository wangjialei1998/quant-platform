from app.core.database import SessionLocal
from app.models.portfolio import Portfolio
from app.services.backtest_execution_service import BacktestExecutionService
from app.tasks.celery_app import celery_app
from app.tasks.chart_tasks import build_chart_snapshots


@celery_app.task(name="app.tasks.backtest_tasks.initialize_portfolio")
def initialize_portfolio(portfolio_id: int) -> dict:
    db = SessionLocal()
    try:
        portfolio = db.get(Portfolio, portfolio_id)
        if not portfolio:
            return {"status": "failed", "message": "Portfolio not found"}
        result = BacktestExecutionService(db).initialize_portfolio(portfolio_id, "initial_backtest")
        if result.get("status") == "success":
            build_chart_snapshots.delay(portfolio_id)
        return result
    finally:
        db.close()
