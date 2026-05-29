from app.core.database import SessionLocal
from app.engines.sandbox_runner import SandboxRunner
from app.models.strategy import Strategy
from app.tasks.celery_app import celery_app
from app.utils.time import utc_now


@celery_app.task(name="app.tasks.strategy_tasks.test_strategy")
def test_strategy(strategy_id: int) -> dict:
    db = SessionLocal()
    try:
        strategy = db.get(Strategy, strategy_id)
        if not strategy:
            return {"status": "failed", "message": "Strategy not found"}
        ok, message = SandboxRunner().validate_strategy_file(strategy.code_path)
        strategy.test_status = "passed" if ok else "failed"
        strategy.test_log = message
        strategy.last_tested_at = utc_now()
        db.commit()
        return {"status": strategy.test_status, "message": message}
    finally:
        db.close()
