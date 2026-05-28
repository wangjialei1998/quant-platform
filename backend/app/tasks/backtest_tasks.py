from datetime import datetime, timezone

from app.core.database import SessionLocal
from app.models.portfolio import Portfolio
from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.backtest_tasks.initialize_portfolio")
def initialize_portfolio(portfolio_id: int) -> dict:
    db = SessionLocal()
    try:
        portfolio = db.get(Portfolio, portfolio_id)
        if not portfolio:
            return {"status": "failed", "message": "Portfolio not found"}
        portfolio.status = "running"
        portfolio.last_run_at = datetime.now(timezone.utc)
        db.commit()
        return {
            "status": "success",
            "message": "组合初始化回测任务接口已建立，回测明细实现待补充",
        }
    finally:
        db.close()
