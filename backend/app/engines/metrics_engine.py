from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class MetricSnapshot:
    metric_date: date
    net_value: float
    total_return: float
    max_drawdown: float
    trade_count: int
    running_days: int


class MetricsEngine:
    def build_empty_snapshot(self, metric_date: date) -> MetricSnapshot:
        return MetricSnapshot(
            metric_date=metric_date,
            net_value=1.0,
            total_return=0.0,
            max_drawdown=0.0,
            trade_count=0,
            running_days=0,
        )

