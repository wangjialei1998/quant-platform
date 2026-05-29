import backtrader as bt


class DualMovingAverageStrategy(bt.Strategy):
    params = (
        ("fast_period", 5),
        ("slow_period", 20),
        ("stake", 100),
    )

    def __init__(self):
        self.fast_ma = {}
        self.slow_ma = {}
        self.crossovers = {}
        self.pending_orders = {}

        for data in self.datas:
            self.fast_ma[data] = bt.indicators.SimpleMovingAverage(
                data.close,
                period=self.p.fast_period,
            )
            self.slow_ma[data] = bt.indicators.SimpleMovingAverage(
                data.close,
                period=self.p.slow_period,
            )
            self.crossovers[data] = bt.indicators.CrossOver(
                self.fast_ma[data],
                self.slow_ma[data],
            )
            self.pending_orders[data] = None

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        data = order.data
        if data in self.pending_orders:
            self.pending_orders[data] = None

    def next(self):
        for data in self.datas:
            if self.pending_orders.get(data):
                continue

            position = self.getposition(data)
            crossover = self.crossovers[data][0]

            if not position and crossover > 0:
                if self.broker.getcash() >= data.close[0] * self.p.stake:
                    self.pending_orders[data] = self.buy(data=data, size=self.p.stake)

            elif position.size > 0 and crossover < 0:
                sell_size = int(position.size // 100) * 100
                if sell_size > 0:
                    self.pending_orders[data] = self.sell(data=data, size=sell_size)
