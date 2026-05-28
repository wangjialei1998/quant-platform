from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "quant_platform",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.strategy_tasks",
        "app.tasks.backtest_tasks",
        "app.tasks.monitor_tasks",
        "app.tasks.market_data_tasks",
        "app.tasks.notification_tasks",
        "app.tasks.chart_tasks",
    ],
)

celery_app.conf.task_routes = {
    "app.tasks.strategy_tasks.*": {"queue": "strategy"},
    "app.tasks.backtest_tasks.*": {"queue": "backtest"},
    "app.tasks.monitor_tasks.*": {"queue": "monitor"},
    "app.tasks.market_data_tasks.*": {"queue": "market_data"},
    "app.tasks.notification_tasks.*": {"queue": "notification"},
    "app.tasks.chart_tasks.*": {"queue": "chart"},
}
celery_app.conf.timezone = "Asia/Shanghai"

