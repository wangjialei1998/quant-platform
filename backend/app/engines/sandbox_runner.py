import ast
import io
import json
import tarfile
from pathlib import Path

import docker

from app.core.config import settings


class SandboxRunner:
    def validate_strategy_file(self, code_path: str) -> tuple[bool, str]:
        path = Path(code_path)
        try:
            source = path.read_text(encoding="utf-8")
            ast.parse(source)
        except Exception as exc:
            return False, str(exc)
        if "backtrader" not in source and "bt.Strategy" not in source and "Strategy" not in source:
            return False, "Strategy file must define a Backtrader Strategy class"

        try:
            result = self.run_backtest(
                strategy_path=path,
                payload={
                    "portfolio": {
                        "initial_cash": "100000",
                        "commission_rate": "0.0003",
                        "stamp_tax_rate": "0.001",
                        "slippage_rate": "0.0002",
                    },
                    "instruments": [{"id": 1, "symbol": "TEST.SZ"}],
                    "bars": {
                        "1": [
                            {"trade_date": "2024-01-02", "open": "10", "high": "10.3", "low": "9.9", "close": "10.1", "volume": "100000", "amount": "1010000"},
                            {"trade_date": "2024-01-03", "open": "10.1", "high": "10.4", "low": "10.0", "close": "10.2", "volume": "100000", "amount": "1020000"},
                            {"trade_date": "2024-01-04", "open": "10.2", "high": "10.5", "low": "10.1", "close": "10.3", "volume": "100000", "amount": "1030000"},
                        ]
                    },
                },
            )
        except Exception as exc:
            return False, str(exc)
        return True, f"Strategy sandbox validation passed. equity_points={len(result.get('equity_curve', []))}"

    def run_backtest(self, strategy_path: Path, payload: dict) -> dict:
        client = docker.from_env()
        image = self._ensure_image(client)
        container = self._create_container(client, image)
        started = False
        try:
            container.put_archive(
                "/",
                _build_archive(
                    {
                        "work/input.json": json.dumps(payload, ensure_ascii=False),
                        "work/strategy.py": strategy_path.read_text(encoding="utf-8"),
                        "work/runner.py": _RUNNER_SCRIPT,
                    }
                ),
            )
            container.start()
            started = True
            wait_result = container.wait(timeout=settings.sandbox_timeout_seconds)
            if wait_result.get("StatusCode") != 0:
                logs = container.logs(stdout=True, stderr=True).decode("utf-8", errors="ignore")
                raise RuntimeError(f"Sandbox exited with code {wait_result.get('StatusCode')}: {logs}")
            stream, _ = container.get_archive("/work/output.json")
            output_bytes = b"".join(stream)
            response = _read_archive_file(output_bytes)
            payload = json.loads(response.decode("utf-8"))
            if payload.get("status") != "success":
                raise RuntimeError(payload.get("message", "Sandbox execution failed"))
            return payload
        except Exception:
            if started:
                try:
                    container.kill()
                except Exception:
                    pass
            raise
        finally:
            try:
                container.remove(force=True)
            except Exception:
                pass

    def _ensure_image(self, client) -> str:
        try:
            client.images.get(settings.sandbox_image)
            return settings.sandbox_image
        except Exception:
            pass
        try:
            client.images.get("quant-api")
            return "quant-api"
        except Exception:
            return settings.sandbox_image

    def _create_container(self, client, image: str):
        return client.containers.create(
            image,
            command=["sh", "-lc", "mkdir -p /work && python /work/runner.py /work/input.json /work/strategy.py /work/output.json"],
            working_dir="/",
            network_disabled=True,
            mem_limit="512m",
            nano_cpus=1_000_000_000,
        )


def _build_archive(files: dict[str, str]) -> bytes:
    archive_buffer = io.BytesIO()
    with tarfile.open(fileobj=archive_buffer, mode="w") as archive:
        directory = tarfile.TarInfo(name="work")
        directory.type = tarfile.DIRTYPE
        directory.mode = 0o755
        archive.addfile(directory)
        for name, content in files.items():
            data = content.encode("utf-8")
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            info.mode = 0o644
            archive.addfile(info, io.BytesIO(data))
    archive_buffer.seek(0)
    return archive_buffer.read()


def _read_archive_file(data: bytes) -> bytes:
    with tarfile.open(fileobj=io.BytesIO(data), mode="r") as archive:
        members = archive.getmembers()
        if not members:
            raise RuntimeError("Sandbox output archive is empty")
        member = members[0]
        extracted = archive.extractfile(member)
        if extracted is None:
            raise RuntimeError("Sandbox output archive is unreadable")
        return extracted.read()


_RUNNER_SCRIPT = r'''
import importlib.util
import inspect
import json
import sys
from datetime import date
from decimal import Decimal

import backtrader as bt
import pandas as pd


class AmountPandasData(bt.feeds.PandasData):
    lines = ("amount",)
    params = (("amount", -1),)


def main():
    input_path, strategy_path, output_path = sys.argv[1:4]
    payload = json.loads(open(input_path, encoding="utf-8").read())
    try:
        result = run(payload, strategy_path)
        result["status"] = "success"
    except Exception as exc:
        result = {"status": "failed", "message": str(exc)}
    open(output_path, "w", encoding="utf-8").write(json.dumps(result, ensure_ascii=False))


def run(payload, strategy_path):
    strategy_cls = load_strategy(strategy_path)
    audit_cls = instrument_strategy(strategy_cls, payload["portfolio"])
    cerebro = bt.Cerebro(stdstats=False)
    portfolio = payload["portfolio"]
    cerebro.broker.setcash(float(portfolio["initial_cash"]))
    cerebro.broker.setcommission(commission=float(portfolio["commission_rate"]))
    cerebro.broker.set_slippage_perc(float(portfolio["slippage_rate"]))
    cerebro.addsizer(bt.sizers.FixedSize, stake=100)

    for instrument in payload["instruments"]:
        rows = payload["bars"].get(str(instrument["id"]), [])
        if not rows:
            continue
        frame = pd.DataFrame(
            [
                {
                    "datetime": row["trade_date"],
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                # TickFlow A-share daily bars expose OHLC fields; for stocks/ETFs
                # this system uses close as the daily settlement-equivalent price
                # for signal calculation and equity marking.
                    "close": float(row["close"]),
                    "volume": float(row.get("volume") or 0),
                    "amount": float(row.get("amount") or 0),
                    "openinterest": 0,
                }
                for row in rows
            ]
        )
        frame["datetime"] = pd.to_datetime(frame["datetime"])
        frame = frame.set_index("datetime")
        cerebro.adddata(AmountPandasData(dataname=frame), name=instrument["symbol"])

    cerebro.addstrategy(audit_cls)
    strategies = cerebro.run(runonce=False)
    strategy = strategies[0]
    return {
        "trades": strategy._audit_trades,
        "positions": strategy._audit_positions,
        "equity_curve": strategy._audit_equity,
    }


def load_strategy(strategy_path):
    spec = importlib.util.spec_from_file_location("user_strategy", strategy_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    candidates = [
        item
        for _, item in inspect.getmembers(module, inspect.isclass)
        if issubclass(item, bt.Strategy) and item is not bt.Strategy and item.__module__ == module.__name__
    ]
    if not candidates:
        raise RuntimeError("Strategy file must define a backtrader.Strategy subclass")
    return candidates[0]


def instrument_strategy(strategy_cls, portfolio):
    class InstrumentedStrategy(strategy_cls):
        def __init__(self):
            super().__init__()
            self._audit_trades = []
            self._audit_positions = []
            self._audit_equity = []
            self._position_costs = {}
            self._last_buy_date = {}
            self._order_signal_dates = {}
            self._last_snapshot_date = None

        def notify_order(self, order):
            super_notify = getattr(super(), "notify_order", None)
            if callable(super_notify):
                super_notify(order)
            if order.status != order.Completed:
                return

            current_date = data_date(order.data)
            signal_date = self._order_signal_dates.pop(order.ref, None)
            symbol = str(order.data._name)
            quantity = decimal(abs(order.executed.size), "0.0001")
            price = decimal(order.executed.price, "0.0001")
            gross = decimal(quantity * price, "0.01")
            side = "buy" if order.isbuy() else "sell"
            commission = decimal(order.executed.comm or 0, "0.01")
            stamp_tax = decimal(gross * Decimal(str(portfolio["stamp_tax_rate"])), "0.01") if side == "sell" else Decimal("0.00")
            slippage = decimal(gross * Decimal(str(portfolio["slippage_rate"])), "0.01")
            net = gross + commission + slippage if side == "buy" else gross - commission - stamp_tax - slippage
            if side == "buy":
                self._position_costs[symbol] = self._position_costs.get(symbol, Decimal("0")) + net
                self._last_buy_date[symbol] = current_date
            else:
                self._position_costs[symbol] = max(self._position_costs.get(symbol, Decimal("0")) - net, Decimal("0"))
            cash = decimal(self.broker.getcash(), "0.01")
            total_asset = decimal(self.broker.getvalue(), "0.01")
            position_value = decimal(total_asset - cash, "0.01")
            self._audit_trades.append(
                {
                    "symbol": symbol,
                    "trade_date": current_date.isoformat(),
                    "signal_date": signal_date.isoformat() if signal_date else None,
                    "side": side,
                    "quantity": str(quantity),
                    "price": str(price),
                    "gross_amount": str(gross),
                    "commission": str(commission),
                    "stamp_tax": str(stamp_tax),
                    "slippage": str(slippage),
                    "net_amount": str(decimal(net, "0.01")),
                    "cash": str(cash),
                    "position_value": str(position_value),
                    "total_asset": str(total_asset),
                    "status": "filled",
                    "reject_reason": None,
                }
            )

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
                self._order_signal_dates[order.ref] = data_date(order.data)

        def next(self):
            user_next = getattr(super(), "next", None)
            if callable(user_next):
                user_next()
            self._capture_signal_dates()
            self._enforce_lot_size_and_t1()
            self._record_snapshot()

        def _capture_signal_dates(self):
            current_date = strategy_date(self)
            for order in list(getattr(self, "_orderspending", [])):
                if order.ref not in self._order_signal_dates:
                    self._order_signal_dates[order.ref] = current_date

        def _enforce_lot_size_and_t1(self):
            current_date = strategy_date(self)
            for order in list(getattr(self, "_orderspending", [])):
                if order.status not in (order.Created, order.Submitted, order.Accepted):
                    continue
                quantity = decimal(abs(order.created.size), "0.0001")
                if quantity % Decimal("100") != 0:
                    self.cancel(order)
                    self._record_rejected_order(order, "quantity must be a 100-share lot")
                    continue
                if order.issell():
                    symbol = str(order.data._name)
                    buy_date = self._last_buy_date.get(symbol)
                    if buy_date is not None and current_date <= buy_date:
                        self.cancel(order)
                        self._record_rejected_order(order, "T+1 sell restriction")

        def _record_rejected_order(self, order, reason):
            current_date = data_date(order.data)
            symbol = str(order.data._name)
            quantity = decimal(abs(order.created.size), "0.0001")
            price = decimal(order.created.price or order.data.close[0], "0.0001")
            gross = decimal(quantity * price, "0.01")
            cash = decimal(self.broker.getcash(), "0.01")
            total_asset = decimal(self.broker.getvalue(), "0.01")
            self._audit_trades.append(
                {
                    "symbol": symbol,
                    "trade_date": current_date.isoformat(),
                    "signal_date": current_date.isoformat(),
                    "side": "buy" if order.isbuy() else "sell",
                    "quantity": str(quantity),
                    "price": str(price),
                    "gross_amount": str(gross),
                    "commission": "0.00",
                    "stamp_tax": "0.00",
                    "slippage": "0.00",
                    "net_amount": "0.00",
                    "cash": str(cash),
                    "position_value": str(decimal(total_asset - cash, "0.01")),
                    "total_asset": str(total_asset),
                    "status": "rejected",
                    "reject_reason": reason,
                }
            )

        def _record_snapshot(self):
            if not self.datas:
                return
            current_date = strategy_date(self)
            if self._last_snapshot_date == current_date:
                return
            self._last_snapshot_date = current_date
            cash = decimal(self.broker.getcash(), "0.01")
            total_asset = decimal(self.broker.getvalue(), "0.01")
            position_value = decimal(total_asset - cash, "0.01")
            self._audit_equity.append(
                {
                    "trade_date": current_date.isoformat(),
                    "cash": str(cash),
                    "position_value": str(position_value),
                    "total_asset": str(total_asset),
                }
            )
            for data in self.datas:
                symbol = str(data._name)
                position = self.getposition(data)
                quantity = decimal(position.size, "0.0001")
                close_price = decimal(data.close[0], "0.0001")
                market_value = decimal(quantity * close_price, "0.01")
                sellable_quantity = Decimal("0.0000")
                if quantity > 0 and self._last_buy_date.get(symbol) != current_date:
                    sellable_quantity = quantity
                weight = float(market_value / total_asset) if total_asset else 0.0
                self._audit_positions.append(
                    {
                        "symbol": symbol,
                        "trade_date": current_date.isoformat(),
                        "quantity": str(quantity),
                        "sellable_quantity": str(sellable_quantity),
                        "cost_amount": str(decimal(self._position_costs.get(symbol, Decimal("0")), "0.01")),
                        "market_value": str(market_value),
                        "weight": weight,
                    }
                )

    return InstrumentedStrategy


def data_date(data):
    return bt.num2date(data.datetime[0]).date()


def strategy_date(strategy):
    return bt.num2date(strategy.datetime[0]).date()


def decimal(value, quant):
    return Decimal(str(value)).quantize(Decimal(quant))


if __name__ == "__main__":
    main()
'''
