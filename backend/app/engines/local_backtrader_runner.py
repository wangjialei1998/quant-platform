"""Local Backtrader runner for development diagnostics.

Production task execution uses SandboxRunner so uploaded strategy code is not
executed in the API or Worker process.
"""

import importlib.util
import inspect
import sys
import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

import backtrader as bt
import pandas as pd

from app.models.instrument import Instrument
from app.models.market_data import MarketDailyBar
from app.models.portfolio import Portfolio
from app.utils.trading_calendar import next_trading_day


class AmountPandasData(bt.feeds.PandasData):
    lines = ("amount",)
    params = (("amount", -1),)


@dataclass(frozen=True)
class EngineTrade:
    symbol: str
    trade_date: date
    signal_date: date | None
    side: str
    quantity: Decimal
    price: Decimal
    gross_amount: Decimal
    commission: Decimal
    stamp_tax: Decimal
    slippage: Decimal
    net_amount: Decimal
    cash: Decimal
    position_value: Decimal
    total_asset: Decimal
    status: str = "filled"
    reject_reason: str | None = None


@dataclass(frozen=True)
class EnginePosition:
    symbol: str
    trade_date: date
    quantity: Decimal
    sellable_quantity: Decimal
    cost_amount: Decimal
    market_value: Decimal
    weight: float


@dataclass(frozen=True)
class EquityPoint:
    trade_date: date
    cash: Decimal
    position_value: Decimal
    total_asset: Decimal


@dataclass(frozen=True)
class BacktestResult:
    start_date: date
    end_date: date
    trades: list[EngineTrade]
    positions: list[EnginePosition]
    equity_curve: list[EquityPoint]


class LocalBacktraderRunner:
    def run_daily_backtest(
        self,
        portfolio: Portfolio,
        instruments: list[Instrument],
        bars_by_instrument: dict[int, list[MarketDailyBar]],
    ) -> BacktestResult:
        if not instruments:
            raise ValueError("Portfolio has no instruments")

        strategy_cls = _load_strategy_class(portfolio.strategy.code_path)
        audit_strategy_cls = _instrument_strategy(strategy_cls, portfolio)
        cerebro = bt.Cerebro(stdstats=False)
        cerebro.broker.setcash(float(portfolio.initial_cash))
        cerebro.broker.setcommission(commission=float(portfolio.commission_rate))
        cerebro.broker.set_slippage_perc(float(portfolio.slippage_rate))
        cerebro.broker.set_coc(True)
        cerebro.addsizer(bt.sizers.FixedSize, stake=100)

        start_date: date | None = None
        end_date: date | None = None
        for instrument in instruments:
            rows = bars_by_instrument.get(instrument.id, [])
            if not rows:
                continue
            start_date = rows[0].trade_date if start_date is None else min(start_date, rows[0].trade_date)
            end_date = rows[-1].trade_date if end_date is None else max(end_date, rows[-1].trade_date)
            cerebro.adddata(_daily_feed(rows), name=instrument.symbol)

        if start_date is None or end_date is None:
            raise ValueError("No market bars available for portfolio instruments")

        cerebro.addstrategy(audit_strategy_cls)
        result = cerebro.run(runonce=False)
        strategy = result[0]
        return BacktestResult(
            start_date=start_date,
            end_date=end_date,
            trades=list(strategy._audit_trades),
            positions=list(strategy._audit_positions),
            equity_curve=list(strategy._audit_equity),
        )


def _daily_feed(rows: list[MarketDailyBar]) -> bt.feeds.PandasData:
    frame = pd.DataFrame(
        [
            {
                "datetime": row.trade_date,
                "open": float(row.open),
                "high": float(row.high),
                "low": float(row.low),
                "close": float(row.close),
                "volume": float(row.volume or 0),
                "amount": float(row.amount or 0),
                "openinterest": 0.0,
            }
            for row in rows
        ]
    )
    frame["datetime"] = pd.to_datetime(frame["datetime"])
    frame = frame.set_index("datetime")
    return AmountPandasData(dataname=frame)


def _load_strategy_class(code_path: str) -> type[bt.Strategy]:
    path = Path(code_path)
    if not path.exists():
        raise FileNotFoundError(f"Strategy code file not found: {code_path}")

    module_name = f"user_strategy_{path.stem}_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if not spec or not spec.loader:
        raise RuntimeError(f"Cannot load strategy module: {code_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(module_name, None)

    candidates = [
        item
        for _, item in inspect.getmembers(module, inspect.isclass)
        if issubclass(item, bt.Strategy) and item is not bt.Strategy and item.__module__ == module.__name__
    ]
    if not candidates:
        raise RuntimeError("Strategy file must define a backtrader.Strategy subclass")
    return candidates[0]


def _instrument_strategy(strategy_cls: type[bt.Strategy], portfolio: Portfolio) -> type[bt.Strategy]:
    class InstrumentedStrategy(strategy_cls):  # type: ignore[misc, valid-type]
        def __init__(self):
            super().__init__()
            self._audit_trades: list[EngineTrade] = []
            self._audit_positions: list[EnginePosition] = []
            self._audit_equity: list[EquityPoint] = []
            self._position_costs: dict[str, Decimal] = {}
            self._last_buy_date: dict[str, date] = {}
            self._order_signal_dates: dict[int, date] = {}
            self._last_snapshot_date: date | None = None

        def notify_order(self, order):
            super_notify = getattr(super(), "notify_order", None)
            if callable(super_notify):
                super_notify(order)
            if order.status != order.Completed:
                return

            current_date = _data_date(order.data)
            signal_date = self._order_signal_dates.pop(order.ref, None)
            symbol = str(order.data._name)
            quantity = Decimal(str(abs(order.executed.size))).quantize(Decimal("0.0001"))
            price = Decimal(str(order.executed.price)).quantize(Decimal("0.0001"))
            gross = (quantity * price).quantize(Decimal("0.01"))
            side = "buy" if order.isbuy() else "sell"
            commission = Decimal(str(order.executed.comm or 0)).quantize(Decimal("0.01"))
            stamp_tax = (gross * Decimal(str(portfolio.stamp_tax_rate))).quantize(Decimal("0.01")) if side == "sell" else Decimal("0.00")
            slippage = (gross * Decimal(str(portfolio.slippage_rate))).quantize(Decimal("0.01"))
            net = gross + commission + slippage if side == "buy" else gross - commission - stamp_tax - slippage

            if side == "buy":
                self._position_costs[symbol] = self._position_costs.get(symbol, Decimal("0")) + net
                self._last_buy_date[symbol] = current_date
            else:
                self._position_costs[symbol] = max(self._position_costs.get(symbol, Decimal("0")) - net, Decimal("0"))

            cash = Decimal(str(self.broker.getcash())).quantize(Decimal("0.01"))
            total_asset = Decimal(str(self.broker.getvalue())).quantize(Decimal("0.01"))
            position_value = (total_asset - cash).quantize(Decimal("0.01"))
            self._audit_trades.append(
                EngineTrade(
                    symbol=symbol,
                    trade_date=current_date,
                    signal_date=signal_date,
                    side=side,
                    quantity=quantity,
                    price=price,
                    gross_amount=gross,
                    commission=commission,
                    stamp_tax=stamp_tax,
                    slippage=slippage,
                    net_amount=net.quantize(Decimal("0.01")),
                    cash=cash,
                    position_value=position_value,
                    total_asset=total_asset,
                )
            )
            self._record_daily_snapshot(force=True)

        def buy(self, *args, **kwargs):
            order = super().buy(*args, **kwargs)
            self._remember_signal_date(order)
            return order

        def sell(self, *args, **kwargs):
            order = super().sell(*args, **kwargs)
            self._remember_signal_date(order)
            return order

        def close(self, *args, **kwargs):
            order = super().close(*args, **kwargs)
            self._remember_signal_date(order)
            return order

        def _remember_signal_date(self, order):
            if order is not None and order.ref not in self._order_signal_dates:
                self._order_signal_dates[order.ref] = _data_date(order.data)

        def next(self):
            user_next = getattr(super(), "next", None)
            if callable(user_next):
                user_next()
            self._capture_signal_dates()
            self._enforce_lot_size_and_t1()
            self._record_daily_snapshot()

        def _capture_signal_dates(self):
            current_date = _strategy_date(self)
            for order in list(getattr(self, "_orderspending", [])):
                if order.ref not in self._order_signal_dates:
                    self._order_signal_dates[order.ref] = current_date

        def _enforce_lot_size_and_t1(self):
            current_date = _strategy_date(self)
            for order in list(getattr(self, "_orderspending", [])):
                if order.status not in (order.Created, order.Submitted, order.Accepted):
                    continue
                quantity = Decimal(str(abs(order.created.size))).quantize(Decimal("0.0001"))
                if quantity % Decimal("100") != 0:
                    self.cancel(order)
                    self._record_rejected_order(order, "quantity must be a 100-share lot")
                    continue
                if order.issell():
                    symbol = str(order.data._name)
                    earliest_trade_date = next_trading_day(self._last_buy_date.get(symbol, current_date))
                    if current_date < earliest_trade_date:
                        self.cancel(order)
                        self._record_rejected_order(order, "T+1 sell restriction")

        def _record_rejected_order(self, order, reason: str):
            current_date = _data_date(order.data)
            symbol = str(order.data._name)
            quantity = Decimal(str(abs(order.created.size))).quantize(Decimal("0.0001"))
            price = Decimal(str(order.created.price or order.data.close[0])).quantize(Decimal("0.0001"))
            cash = Decimal(str(self.broker.getcash())).quantize(Decimal("0.01"))
            total_asset = Decimal(str(self.broker.getvalue())).quantize(Decimal("0.01"))
            self._audit_trades.append(
                EngineTrade(
                    symbol=symbol,
                    trade_date=current_date,
                    signal_date=current_date,
                    side="buy" if order.isbuy() else "sell",
                    quantity=quantity,
                    price=price,
                    gross_amount=(quantity * price).quantize(Decimal("0.01")),
                    commission=Decimal("0.00"),
                    stamp_tax=Decimal("0.00"),
                    slippage=Decimal("0.00"),
                    net_amount=Decimal("0.00"),
                    cash=cash,
                    position_value=(total_asset - cash).quantize(Decimal("0.01")),
                    total_asset=total_asset,
                    status="rejected",
                    reject_reason=reason,
                )
            )

        def _record_daily_snapshot(self, force: bool = False):
            if not self.datas:
                return
            current_date = _strategy_date(self)
            if self._last_snapshot_date == current_date and not force:
                return
            if force:
                self._audit_equity = [
                    item for item in self._audit_equity if item.trade_date != current_date
                ]
                self._audit_positions = [
                    item for item in self._audit_positions if item.trade_date != current_date
                ]
            self._last_snapshot_date = current_date
            cash = Decimal(str(self.broker.getcash())).quantize(Decimal("0.01"))
            total_asset = Decimal(str(self.broker.getvalue())).quantize(Decimal("0.01"))
            position_value = (total_asset - cash).quantize(Decimal("0.01"))
            self._audit_equity.append(
                EquityPoint(
                    trade_date=current_date,
                    cash=cash,
                    position_value=position_value,
                    total_asset=total_asset,
                )
            )

            for data in self.datas:
                symbol = str(data._name)
                position = self.getposition(data)
                quantity = Decimal(str(position.size)).quantize(Decimal("0.0001"))
                close_price = Decimal(str(data.close[0])).quantize(Decimal("0.0001"))
                market_value = (quantity * close_price).quantize(Decimal("0.01"))
                sellable_quantity = Decimal("0.0000")
                if quantity > 0 and self._last_buy_date.get(symbol) != current_date:
                    sellable_quantity = quantity
                weight = float(market_value / total_asset) if total_asset else 0.0
                self._audit_positions.append(
                    EnginePosition(
                        symbol=symbol,
                        trade_date=current_date,
                        quantity=quantity,
                        sellable_quantity=sellable_quantity,
                        cost_amount=self._position_costs.get(symbol, Decimal("0")).quantize(Decimal("0.01")),
                        market_value=market_value,
                        weight=weight,
                    )
                )

    InstrumentedStrategy.__name__ = f"Instrumented{strategy_cls.__name__}"
    return InstrumentedStrategy


def _data_date(data) -> date:
    return bt.num2date(data.datetime[0]).date()


def _strategy_date(strategy) -> date:
    return bt.num2date(strategy.datetime[0]).date()
