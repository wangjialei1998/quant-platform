import backtrader as bt

class AmountProbeStrategy(bt.Strategy):
    def next(self):
        _ = self.data.amount[0]
