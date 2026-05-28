from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.chart_tasks.build_chart_snapshots")
def build_chart_snapshots(portfolio_id: int) -> dict:
    return {
        "status": "success",
        "portfolio_id": portfolio_id,
        "message": "图表预计算任务接口已建立，明细计算待补充",
    }

