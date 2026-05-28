from fastapi import APIRouter

from app.api import instruments, logs, market_data, portfolios, settings, signals, strategies, tasks

api_router = APIRouter()
api_router.include_router(strategies.router, prefix="/strategies", tags=["strategies"])
api_router.include_router(instruments.router, prefix="/instruments", tags=["instruments"])
api_router.include_router(portfolios.router, prefix="/portfolios", tags=["portfolios"])
api_router.include_router(market_data.router, prefix="/market-data", tags=["market-data"])
api_router.include_router(signals.router, prefix="/portfolios", tags=["signals"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(logs.router, prefix="/logs", tags=["logs"])
