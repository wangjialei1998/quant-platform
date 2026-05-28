from sqlalchemy.orm import Session


class ChartService:
    def __init__(self, db: Session):
        self.db = db

    def empty_series(self) -> dict:
        return {"dates": [], "series": []}

