from app.models.strategy import Strategy
from app.repositories.base import Repository


class StrategyRepository(Repository[Strategy]):
    model = Strategy

