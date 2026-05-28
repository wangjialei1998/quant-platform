class ChartBuilder:
    def empty_equity_curve(self) -> dict:
        return {"dates": [], "portfolio": [], "benchmark": []}

    def empty_drawdown(self) -> dict:
        return {"dates": [], "drawdown": []}

