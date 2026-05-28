from datetime import date


class TickFlowClient:
    def fetch_daily_bars(self, symbol: str, start_date: date, end_date: date) -> list[dict]:
        raise NotImplementedError("TickFlow 免费接口适配尚未实现")

