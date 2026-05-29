from datetime import datetime, timezone

from app.core.database import SessionLocal
from app.models.portfolio import Portfolio
from app.services.demo_backtest_service import DemoBacktestService
from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.backtest_tasks.initialize_portfolio")
def initialize_portfolio(portfolio_id: int) -> dict:
    db = SessionLocal()
    try:
        portfolio = db.get(Portfolio, portfolio_id)
        if not portfolio:
            return {"status": "failed", "message": "Portfolio not found"}
        return DemoBacktestService(db).initialize_portfolio(portfolio_id)
    finally:
        db.close()
