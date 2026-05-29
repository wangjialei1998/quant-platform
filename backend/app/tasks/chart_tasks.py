from app.core.database import SessionLocal
from app.services.chart_service import ChartService
from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.chart_tasks.build_chart_snapshots")
def build_chart_snapshots(portfolio_id: int) -> dict:
    db = SessionLocal()
    try:
        return ChartService(db).build_portfolio_snapshots(portfolio_id)
    except Exception as exc:
        db.rollback()
        return {"status": "failed", "portfolio_id": portfolio_id, "message": str(exc)}
    finally:
        db.close()
