class SignalInsightEngine:
    def empty_distribution(self) -> dict:
        return {"holding_days": 0, "empty_days": 0, "holding_ratio": 0.0}

    def empty_effectiveness(self) -> dict:
        return {"buy": {"day_5": None, "day_20": None}, "sell": {"day_5": None, "day_20": None}}

    def empty_frequency(self) -> dict:
        return {"total": 0, "avg_interval_days": None, "buy_count": 0, "sell_count": 0}

    def empty_risks(self) -> list[dict]:
        return []

