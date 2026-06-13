from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from statistics import mean, pstdev

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.engines.backtrader_engine import BacktraderEngine
from app.models.backtest import BacktestRun
from app.models.instrument import Instrument
from app.models.log import SystemLog
from app.models.market_data import MarketDailyBar
from app.models.metric import PortfolioMetric
from app.models.portfolio import Portfolio, PortfolioInstrument, PortfolioPosition
from app.models.signal import Signal
from app.models.trade import CashFlow, Trade
from app.services.market_data_service import MarketDataService
from app.services.notification_service import NotificationService
from app.services.portfolio_report_email_service import PortfolioReportEmailService
from app.utils.time import utc_now
from app.utils.trading_calendar import is_trading_day


@dataclass(frozen=True)
class SandboxTrade:
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
    status: str
    reject_reason: str | None


@dataclass(frozen=True)
class SandboxPosition:
    symbol: str
    trade_date: date
    quantity: Decimal
    sellable_quantity: Decimal
    cost_amount: Decimal
    market_value: Decimal
    weight: float


@dataclass(frozen=True)
class SandboxEquity:
    trade_date: date
    cash: Decimal
    position_value: Decimal
    total_asset: Decimal


class BacktestExecutionService:
    def __init__(self, db: Session):
        self.db = db

    def initialize_portfolio(self, portfolio_id: int, run_type: str = "initial_backtest") -> dict:
        portfolio = self.db.get(Portfolio, portfolio_id)
        if not portfolio:
            return {"status": "failed", "message": "Portfolio not found"}

        run = BacktestRun(
            portfolio_id=portfolio.id,
            run_type=run_type,
            status="running",
            start_date=portfolio.start_date,
            end_date=self._latest_trading_date(portfolio.start_date),
            started_at=utc_now(),
            created_at=utc_now(),
        )
        self.db.add(run)
        portfolio.status = "initializing"
        self.db.commit()
        self.db.refresh(run)
        self.db.refresh(portfolio)

        try:
            instruments = self._portfolio_instruments(portfolio.id)
            if not instruments:
                raise RuntimeError("Portfolio has no instruments")

            end_date = run.end_date or self._latest_trading_date(portfolio.start_date)
            MarketDataService(self.db).ensure_daily_bars(instruments, portfolio.start_date, end_date)
            bars_by_instrument = self._bars_by_instrument(instruments, portfolio.start_date, end_date)
            self._assert_complete_bars(instruments, bars_by_instrument)

            payload = self._sandbox_payload(portfolio, instruments, bars_by_instrument)
            sandbox_result = BacktraderEngine().run_daily_backtest(portfolio.strategy.code_path, payload)
            trades, positions, equity_curve = self._parse_sandbox_result(sandbox_result)

            self._clear_portfolio_outputs(portfolio.id)
            notification_ids = self._persist_result(portfolio, instruments, trades, positions, equity_curve, run.id)

            run.status = "success"
            if equity_curve:
                run.start_date = equity_curve[0].trade_date
                run.end_date = equity_curve[-1].trade_date
            run.finished_at = utc_now()
            portfolio.status = "running"
            portfolio.last_run_at = utc_now()
            self.db.commit()
            NotificationService.enqueue(notification_ids)
            return {
                "status": "success",
                "message": "Backtrader sandbox backtest completed",
                "portfolio_id": portfolio_id,
                "run_id": run.id,
                "trade_count": len([item for item in trades if item.status == "filled"]),
                "running_days": len(equity_curve),
            }
        except Exception as exc:
            self.db.rollback()
            self._mark_failed(portfolio_id, run.id, str(exc))
            return {"status": "failed", "message": str(exc), "portfolio_id": portfolio_id, "run_id": run.id}

    def _portfolio_instruments(self, portfolio_id: int) -> list[Instrument]:
        return (
            self.db.query(Instrument)
            .join(PortfolioInstrument, PortfolioInstrument.instrument_id == Instrument.id)
            .filter(PortfolioInstrument.portfolio_id == portfolio_id, Instrument.is_active.is_(True))
            .order_by(PortfolioInstrument.sort_order, PortfolioInstrument.id)
            .all()
        )

    def _latest_trading_date(self, start_date: date) -> date:
        current = date.today()
        if current < start_date:
            current = start_date
        while not is_trading_day(current):
            from datetime import timedelta

            current -= timedelta(days=1)
        return current

    def _bars_by_instrument(
        self,
        instruments: list[Instrument],
        start_date: date,
        end_date: date,
    ) -> dict[int, list[MarketDailyBar]]:
        rows = (
            self.db.query(MarketDailyBar)
            .filter(
                MarketDailyBar.instrument_id.in_([item.id for item in instruments] or [0]),
                MarketDailyBar.trade_date >= start_date,
                MarketDailyBar.trade_date <= end_date,
                MarketDailyBar.adjustment_type == "none",
                MarketDailyBar.is_suspended.is_(False),
            )
            .order_by(MarketDailyBar.instrument_id, MarketDailyBar.trade_date)
            .all()
        )
        grouped: dict[int, list[MarketDailyBar]] = {item.id: [] for item in instruments}
        for row in rows:
            grouped.setdefault(row.instrument_id, []).append(row)
        return grouped

    def _assert_complete_bars(self, instruments: list[Instrument], bars_by_instrument: dict[int, list[MarketDailyBar]]) -> None:
        missing = [item.symbol for item in instruments if not bars_by_instrument.get(item.id)]
        if missing:
            raise RuntimeError(f"No cached daily bars available after TickFlow sync: {', '.join(missing)}")

    def _sandbox_payload(
        self,
        portfolio: Portfolio,
        instruments: list[Instrument],
        bars_by_instrument: dict[int, list[MarketDailyBar]],
    ) -> dict:
        return {
            "portfolio": {
                "initial_cash": str(portfolio.initial_cash),
                "commission_rate": str(portfolio.commission_rate),
                "stamp_tax_rate": str(portfolio.stamp_tax_rate),
                "slippage_rate": str(portfolio.slippage_rate),
            },
            "instruments": [{"id": item.id, "symbol": item.symbol} for item in instruments],
            "bars": {
                str(instrument_id): [
                    {
                        "trade_date": row.trade_date.isoformat(),
                        "open": str(row.open),
                        "high": str(row.high),
                        "low": str(row.low),
                        "close": str(row.close),
                        "volume": str(row.volume or 0),
                    }
                    for row in rows
                ]
                for instrument_id, rows in bars_by_instrument.items()
            },
        }

    def _parse_sandbox_result(
        self,
        result: dict,
    ) -> tuple[list[SandboxTrade], list[SandboxPosition], list[SandboxEquity]]:
        trades = [
            SandboxTrade(
                symbol=item["symbol"],
                trade_date=date.fromisoformat(item["trade_date"]),
                signal_date=date.fromisoformat(item["signal_date"]) if item.get("signal_date") else None,
                side=item["side"],
                quantity=Decimal(item["quantity"]),
                price=Decimal(item["price"]),
                gross_amount=Decimal(item["gross_amount"]),
                commission=Decimal(item["commission"]),
                stamp_tax=Decimal(item["stamp_tax"]),
                slippage=Decimal(item["slippage"]),
                net_amount=Decimal(item["net_amount"]),
                cash=Decimal(item["cash"]),
                position_value=Decimal(item["position_value"]),
                total_asset=Decimal(item["total_asset"]),
                status=item.get("status", "filled"),
                reject_reason=item.get("reject_reason"),
            )
            for item in result.get("trades", [])
        ]
        positions = [
            SandboxPosition(
                symbol=item["symbol"],
                trade_date=date.fromisoformat(item["trade_date"]),
                quantity=Decimal(item["quantity"]),
                sellable_quantity=Decimal(item["sellable_quantity"]),
                cost_amount=Decimal(item["cost_amount"]),
                market_value=Decimal(item["market_value"]),
                weight=float(item["weight"]),
            )
            for item in result.get("positions", [])
        ]
        equity_curve = [
            SandboxEquity(
                trade_date=date.fromisoformat(item["trade_date"]),
                cash=Decimal(item["cash"]),
                position_value=Decimal(item["position_value"]),
                total_asset=Decimal(item["total_asset"]),
            )
            for item in result.get("equity_curve", [])
        ]
        return trades, positions, equity_curve

    def _clear_portfolio_outputs(self, portfolio_id: int) -> None:
        from app.models.notification import Notification

        for model in (PortfolioMetric, PortfolioPosition, CashFlow, Trade, Signal):
            self.db.execute(delete(model).where(model.portfolio_id == portfolio_id))
        self.db.execute(delete(Notification).where(Notification.portfolio_id == portfolio_id))
        self.db.flush()

    def _persist_result(
        self,
        portfolio: Portfolio,
        instruments: list[Instrument],
        trades: list[SandboxTrade],
        positions: list[SandboxPosition],
        equity_curve: list[SandboxEquity],
        run_id: int,
    ) -> list[int]:
        instrument_by_symbol = {item.symbol: item for item in instruments}
        notification_ids = self._persist_trades_and_signals(portfolio, instrument_by_symbol, trades, run_id)
        self._persist_positions(portfolio, instrument_by_symbol, positions)
        self._persist_metrics(portfolio, equity_curve, [trade for trade in trades if trade.status == "filled"])
        self.db.flush()
        report_notification_id = PortfolioReportEmailService(self.db).create_report_notification(
            portfolio,
            run_id=run_id,
            force=False,
        )
        if report_notification_id:
            notification_ids.append(report_notification_id)
        return notification_ids

    def _persist_trades_and_signals(
        self,
        portfolio: Portfolio,
        instrument_by_symbol: dict[str, Instrument],
        trades: list[SandboxTrade],
        run_id: int,
    ) -> list[int]:
        notification_ids: list[int] = []
        for item in trades:
            instrument = instrument_by_symbol.get(item.symbol)
            if not instrument:
                continue
            signal = Signal(
                portfolio_id=portfolio.id,
                instrument_id=instrument.id,
                run_id=run_id,
                signal_date=item.signal_date or item.trade_date,
                side=item.side,
                price=item.price,
                status="traded" if item.status == "filled" else "rejected",
                email_status="pending" if portfolio.email_enabled else "disabled",
                created_at=utc_now(),
            )
            self.db.add(signal)
            self.db.flush()

            if False:
                signal_title = f"{portfolio.name} {instrument.symbol} {item.side.upper()} 信号"
                signal_content = "\n".join(
                    [
                        f"组合：{portfolio.name}",
                        f"标的：{instrument.symbol} {instrument.name}",
                        f"信号方向：{item.side}",
                        f"信号日期：{signal.signal_date}",
                        f"参考价格：{item.price}",
                        f"状态：{signal.status}",
                    ]
                )
                notification_ids.append(
                    notification_service.create_event(portfolio, "signal", signal_title, signal_content).id
                )

            trade = Trade(
                portfolio_id=portfolio.id,
                instrument_id=instrument.id,
                run_id=run_id,
                signal_id=signal.id,
                signal_date=signal.signal_date,
                trade_date=item.trade_date,
                side=item.side,
                quantity=item.quantity,
                price=item.price,
                gross_amount=item.gross_amount,
                commission=item.commission,
                stamp_tax=item.stamp_tax,
                slippage=item.slippage,
                net_amount=item.net_amount,
                status=item.status,
                reject_reason=item.reject_reason,
                created_at=utc_now(),
            )
            self.db.add(trade)

            if item.status == "filled":
                amount = -item.net_amount if item.side == "buy" else item.net_amount
                self.db.add(
                    CashFlow(
                        portfolio_id=portfolio.id,
                        run_id=run_id,
                        flow_date=item.trade_date,
                        flow_type=item.side,
                        amount=amount,
                        available_cash=item.cash,
                        position_value=item.position_value,
                        total_asset=item.total_asset,
                        created_at=utc_now(),
                    )
                )
                if False:
                    trade_title = f"{portfolio.name} {instrument.symbol} {item.side.upper()} 成交"
                    trade_content = "\n".join(
                        [
                            f"组合：{portfolio.name}",
                            f"标的：{instrument.symbol} {instrument.name}",
                            f"成交方向：{item.side}",
                            f"信号日期：{signal.signal_date}",
                            f"成交日期：{item.trade_date}",
                            f"价格：{item.price}",
                            f"数量：{item.quantity}",
                            f"成交金额：{item.gross_amount}",
                            f"费用：佣金 {item.commission}，印花税 {item.stamp_tax}，滑点 {item.slippage}",
                            f"当前总资产：{item.total_asset}",
                        ]
                    )
                    notification_ids.append(
                        notification_service.create_event(portfolio, "trade", trade_title, trade_content).id
                    )
        return notification_ids

    def _persist_positions(
        self,
        portfolio: Portfolio,
        instrument_by_symbol: dict[str, Instrument],
        positions: list[SandboxPosition],
    ) -> None:
        for item in positions:
            instrument = instrument_by_symbol.get(item.symbol)
            if not instrument:
                continue
            self.db.add(
                PortfolioPosition(
                    portfolio_id=portfolio.id,
                    instrument_id=instrument.id,
                    trade_date=item.trade_date,
                    quantity=item.quantity,
                    sellable_quantity=item.sellable_quantity,
                    cost_amount=item.cost_amount,
                    market_value=item.market_value,
                    weight=item.weight,
                )
            )

    def _persist_metrics(
        self,
        portfolio: Portfolio,
        equity_curve: list[SandboxEquity],
        filled_trades: list[SandboxTrade],
    ) -> None:
        if not equity_curve:
            return

        peak_asset = portfolio.initial_cash
        max_drawdown = 0.0
        max_drawdown_days = 0
        drawdown_start_index = 0
        previous_asset: Decimal | None = None
        daily_returns: list[float] = []

        for index, point in enumerate(equity_curve, start=1):
            total_asset = point.total_asset
            if total_asset >= peak_asset:
                peak_asset = total_asset
                drawdown_start_index = index
            drawdown = float((total_asset - peak_asset) / peak_asset) if peak_asset else 0.0
            if drawdown < max_drawdown:
                max_drawdown = drawdown
                max_drawdown_days = index - drawdown_start_index
            if previous_asset and previous_asset > 0:
                daily_returns.append(float(total_asset / previous_asset - 1))
            previous_asset = total_asset

            net_value = float(total_asset / portfolio.initial_cash)
            annual_return = net_value ** (252 / max(index, 1)) - 1 if net_value > 0 else 0.0
            volatility = pstdev(daily_returns) * (252**0.5) if len(daily_returns) > 1 else 0.0
            sharpe = (
                mean(daily_returns) / pstdev(daily_returns) * (252**0.5)
                if len(daily_returns) > 1 and pstdev(daily_returns)
                else 0.0
            )
            completed_trades = [trade for trade in filled_trades if trade.trade_date <= point.trade_date]
            closed_trade_returns, closed_trade_pnls = _closed_trade_results(completed_trades)
            profit_loss_ratio, win_rate = _trade_quality(closed_trade_pnls)
            sqn = _sqn(closed_trade_returns)
            self.db.add(
                PortfolioMetric(
                    portfolio_id=portfolio.id,
                    metric_date=point.trade_date,
                    net_value=net_value,
                    total_return=net_value - 1,
                    annual_return=annual_return,
                    win_rate=win_rate,
                    profit_loss_ratio=profit_loss_ratio,
                    sharpe_ratio=sharpe,
                    current_drawdown=drawdown,
                    max_drawdown=max_drawdown,
                    max_drawdown_days=max_drawdown_days,
                    volatility=volatility,
                    sqn=sqn,
                    vwr=_vwr(equity_curve[:index], annual_return),
                    trade_count=len(completed_trades),
                    running_days=index,
                    created_at=utc_now(),
                )
            )

    def _mark_failed(self, portfolio_id: int, run_id: int, message: str) -> None:
        run = self.db.get(BacktestRun, run_id)
        portfolio = self.db.get(Portfolio, portfolio_id)
        if run:
            run.status = "failed"
            run.error_message = message
            run.finished_at = utc_now()
        if portfolio:
            portfolio.status = "failed"
            portfolio.last_run_at = utc_now()
        self.db.add(
            SystemLog(
                level="error",
                module="backtest",
                message=message,
                context={"portfolio_id": portfolio_id, "run_id": run_id},
                portfolio_id=portfolio_id,
                strategy_id=None,
                run_id=run_id,
                created_at=utc_now(),
            )
        )
        notification_id = None
        if portfolio and portfolio.email_enabled:
            notification = NotificationService(self.db).create_event(
                portfolio,
                "error",
                f"{portfolio.name} 运行失败",
                "\n".join(
                    [
                        f"组合：{portfolio.name}",
                        f"运行ID：{run_id}",
                        f"错误摘要：{message}",
                    ]
                ),
            )
            notification_id = notification.id
        self.db.commit()
        if notification_id:
            NotificationService.enqueue([notification_id])


def _closed_trade_results(trades: list[SandboxTrade]) -> tuple[list[float], list[float]]:
    positions: dict[str, dict[str, Decimal]] = {}
    returns: list[float] = []
    pnls: list[float] = []
    for trade in sorted(trades, key=lambda item: (item.trade_date, item.symbol, item.side)):
        if trade.status != "filled" or trade.quantity <= 0:
            continue
        position = positions.setdefault(trade.symbol, {"quantity": Decimal("0"), "cost": Decimal("0")})
        if trade.side == "buy":
            position["quantity"] += trade.quantity
            position["cost"] += trade.net_amount
            continue
        if trade.side != "sell" or position["quantity"] <= 0 or position["cost"] <= 0:
            continue

        closed_quantity = min(trade.quantity, position["quantity"])
        quantity_ratio = closed_quantity / position["quantity"]
        sell_ratio = closed_quantity / trade.quantity
        cost_basis = position["cost"] * quantity_ratio
        proceeds = trade.net_amount * sell_ratio
        pnl = proceeds - cost_basis
        if cost_basis > 0:
            returns.append(float(pnl / cost_basis))
            pnls.append(float(pnl))
        position["quantity"] -= closed_quantity
        position["cost"] -= cost_basis
        if position["quantity"] <= 0:
            position["quantity"] = Decimal("0")
            position["cost"] = Decimal("0")
    return returns, pnls


def _trade_quality(pnls: list[float]) -> tuple[float, float]:
    wins = [item for item in pnls if item > 0]
    losses = [abs(item) for item in pnls if item < 0]
    win_rate = len(wins) / len(pnls) if pnls else 0.0
    profit_loss_ratio = (mean(wins) / mean(losses)) if wins and losses else 0.0
    return profit_loss_ratio, win_rate


def _sqn(returns: list[float]) -> float:
    if len(returns) < 2:
        return 0.0
    deviation = pstdev(returns)
    if not deviation:
        return 0.0
    return (len(returns) ** 0.5) * mean(returns) / deviation


def _vwr(equity_curve: list[SandboxEquity], annual_return: float) -> float:
    if len(equity_curve) < 2:
        return annual_return
    values = [float(point.total_asset) for point in equity_curve if point.total_asset > 0]
    if len(values) < 2 or values[0] <= 0 or values[-1] <= 0:
        return 0.0
    growth = (values[-1] / values[0]) ** (1 / (len(values) - 1))
    deviations = []
    for index, value in enumerate(values):
        expected = values[0] * (growth**index)
        if expected > 0:
            deviations.append(value / expected - 1)
    variability = pstdev(deviations) if len(deviations) > 1 else 0.0
    penalty = max(0.0, 1 - (variability / 2.0) ** 0.20)
    return annual_return * penalty
