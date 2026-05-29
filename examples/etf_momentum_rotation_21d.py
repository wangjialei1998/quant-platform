import backtrader as bt


class ETFMomentumRotation21Strategy(bt.Strategy):
    params = (
        ("lookback", 21),
        ("rebalance_interval", 1),
        ("invest_ratio", 0.95),
        ("lot_size", 100),
        ("min_momentum", None),
    )

    def __init__(self):
        self.pending_orders = {}
        self.bar_count = 0
        for data in self.datas:
            self.pending_orders[data] = None

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.data in self.pending_orders:
            self.pending_orders[order.data] = None

    def next(self):
        self.bar_count += 1
        if self._has_pending_order():
            return
        if self.bar_count % self.p.rebalance_interval != 0:
            return

        target = self._select_strongest_etf()
        if target is None:
            self._sell_all_positions()
            return

        sold_non_target = False
        for data in self.datas:
            if data is target:
                continue
            if self._sell_position(data):
                sold_non_target = True

        # Let sell orders execute first. The next rebalance can use settled cash
        # to buy the new strongest ETF.
        if sold_non_target:
            return

        target_position = self.getposition(target)
        if target_position.size <= 0:
            self._buy_target(target)

    def _select_strongest_etf(self):
        candidates = []
        for data in self.datas:
            if len(data) <= self.p.lookback:
                continue
            current_close = float(data.close[0])
            past_close = float(data.close[-self.p.lookback])
            if current_close <= 0 or past_close <= 0:
                continue
            momentum = current_close / past_close - 1
            candidates.append((momentum, data))

        if not candidates:
            return None

        candidates.sort(key=lambda item: item[0], reverse=True)
        best_momentum, best_data = candidates[0]
        if self.p.min_momentum is not None and best_momentum < self.p.min_momentum:
            return None
        return best_data

    def _has_pending_order(self):
        return any(order is not None for order in self.pending_orders.values())

    def _sell_all_positions(self):
        for data in self.datas:
            self._sell_position(data)

    def _sell_position(self, data):
        position = self.getposition(data)
        sell_size = int(position.size // self.p.lot_size) * self.p.lot_size
        if sell_size <= 0:
            return False
        self.pending_orders[data] = self.sell(data=data, size=sell_size)
        return True

    def _buy_target(self, data):
        price = float(data.close[0])
        if price <= 0:
            return

        cash_to_use = float(self.broker.getcash()) * float(self.p.invest_ratio)
        buy_size = int((cash_to_use / price) // self.p.lot_size) * self.p.lot_size
        if buy_size <= 0:
            return
        self.pending_orders[data] = self.buy(data=data, size=buy_size)
