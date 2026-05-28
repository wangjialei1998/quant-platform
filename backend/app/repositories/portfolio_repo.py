from app.models.portfolio import Portfolio
from app.repositories.base import Repository


class PortfolioRepository(Repository[Portfolio]):
    model = Portfolio

