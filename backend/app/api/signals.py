from fastapi import APIRouter

from app.engines.signal_insight_engine import SignalInsightEngine

router = APIRouter()


@router.get("/{portfolio_id}/signals/price-chart")
def price_chart(portfolio_id: int) -> dict:
    return {"dates": [], "series": [], "signals": []}


@router.get("/{portfolio_id}/signals/distribution")
def distribution(portfolio_id: int) -> dict:
    return SignalInsightEngine().empty_distribution()


@router.get("/{portfolio_id}/signals/effectiveness")
def effectiveness(portfolio_id: int) -> dict:
    return SignalInsightEngine().empty_effectiveness()


@router.get("/{portfolio_id}/signals/frequency")
def frequency(portfolio_id: int) -> dict:
    return SignalInsightEngine().empty_frequency()


@router.get("/{portfolio_id}/signals/risks")
def risks(portfolio_id: int) -> list[dict]:
    return SignalInsightEngine().empty_risks()


@router.get("/{portfolio_id}/signals/volatility")
def volatility(portfolio_id: int) -> dict:
    return {"months": [], "series": []}

