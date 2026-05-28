from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.market_data_tasks.sync_market_data")
def sync_market_data(instrument_ids: list[int], start_date: str, end_date: str) -> dict:
    return {
        "status": "success",
        "instrument_ids": instrument_ids,
        "start_date": start_date,
        "end_date": end_date,
        "message": "行情同步任务接口已建立，TickFlow 适配待补充",
    }

