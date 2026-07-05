from celery import Celery
from celery.schedules import crontab

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
celery_app.conf.beat_schedule = {
    "daily-monitor-after-market-close": {
        "task": "app.tasks.market_data_tasks.sync_running_portfolio_market_data",
        "schedule": crontab(hour=15, minute=0),
        "kwargs": {"run_monitors": True},
        "options": {"queue": "market_data"},
    },
}
