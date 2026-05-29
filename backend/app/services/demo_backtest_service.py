from datetime import date, timedelta
from decimal import Decimal
from statistics import mean, pstdev

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.engines.trading_rules import TradeRequest, TradingRules
from app.models.instrument import Instrument
from app.models.market_data import MarketDailyBar
from app.models.metric import PortfolioMetric
from app.models.portfolio import Portfolio, PortfolioInstrument, PortfolioPosition
from app.models.signal import Signal
from app.models.trade import CashFlow, Trade
from app.utils.time import utc_now
from app.utils.trading_calendar import is_trading_day


class DemoBacktestService:
    """Deterministic local backtest path used before real TickFlow/Backtrader is wired."""

    def __init__(self, db: Session):
        self.db = db
        self.rules = TradingRules()

    def initialize_portfolio(self, portfolio_id: int) -> dict:
        portfolio = self.db.get(Portfolio, portfolio_id)
        if not portfolio:
            return {"status": "failed", "message": "Portfolio not found"}

        instruments = self._portfolio_instruments(portfolio.id)
        if not instruments:
            return {"status": "failed", "message": "Portfolio has no instruments"}

        end_date = self._latest_demo_date(portfolio.start_date)
        for index, instrument in enumerate(instruments):
            self._ensure_demo_bars(instrument, portfolio.start_date, end_date, index)

        self._clear_portfolio_outputs(portfolio.id)
        result = self._run_simple_simulation(portfolio, instruments, portfolio.start_date, end_date)

        portfolio.status = "running"
        portfolio.last_run_at = utc_now()
        self.db.commit()
        return {
            "status": "success",
            "message": "演示回测已完成",
            "portfolio_id": portfolio_id,
            **result,
        }

    def _portfolio_instruments(self, portfolio_id: int) -> list[Instrument]:
        rows = (
            self.db.query(Instrument)
            .join(PortfolioInstrument, PortfolioInstrument.instrument_id == Instrument.id)
            .filter(PortfolioInstrument.portfolio_id == portfolio_id)
            .order_by(Instrument.symbol)
            .all()
        )
        return rows

    def _latest_demo_date(self, start_date: date) -> date:
        candidate = date.today()
        if candidate <= start_date:
            candidate = start_date + timedelta(days=90)
        while not is_trading_day(candidate):
            candidate -= timedelta(days=1)
        return candidate

    def _ensure_demo_bars(self, instrument: Instrument, start_date: date, end_date: date, offset: int) -> None:
        existing = (
            self.db.query(MarketDailyBar)
            .filter(
                MarketDailyBar.instrument_id == instrument.id,
                MarketDailyBar.trade_date >= start_date,
                MarketDailyBar.trade_date <= end_date,
            )
            .count()
        )
        if existing:
            return

        price = Decimal("10.00") + Decimal(offset * 3)
        day = start_date
        sequence = 0
        while day <= end_date:
            if is_trading_day(day):
                wave = Decimal((sequence % 17) - 8) / Decimal("100")
                drift = Decimal(sequence) * Decimal("0.015")
                close = max(Decimal("1"), price + drift + wave)
                open_price = close * Decimal("0.995")
                high = close * Decimal("1.015")
                low = close * Decimal("0.985")
                self.db.add(
                    MarketDailyBar(
                        instrument_id=instrument.id,
                        trade_date=day,
                        open=open_price,
                        high=high,
                        low=low,
                        close=close,
                        volume=Decimal("1000000") + Decimal(sequence * 1000),
                        amount=close * Decimal("1000000"),
                        limit_up=close * Decimal("1.1"),
                        limit_down=close * Decimal("0.9"),
                        is_suspended=False,
                        adjustment_type="none",
                        source="demo",
                    )
                )
                sequence += 1
            day += timedelta(days=1)
        self.db.flush()

    def _clear_portfolio_outputs(self, portfolio_id: int) -> None:
        for model in (PortfolioMetric, PortfolioPosition, CashFlow, Trade, Signal):
            self.db.execute(delete(model).where(model.portfolio_id == portfolio_id))
        self.db.flush()

    def _run_simple_simulation(
        self,
        portfolio: Portfolio,
        instruments: list[Instrument],
        start_date: date,
        end_date: date,
    ) -> dict:
        cash = portfolio.initial_cash
        holdings: dict[int, Decimal] = {item.id: Decimal("0") for item in instruments}
        sellable: dict[int, Decimal] = {item.id: Decimal("0") for item in instruments}
        costs: dict[int, Decimal] = {item.id: Decimal("0") for item in instruments}
        peak_asset = portfolio.initial_cash
        max_drawdown = 0.0
        max_drawdown_days = 0
        drawdown_start_index = 0
        trade_count = 0
        running_days = 0
        daily_returns: list[float] = []
        previous_asset: Decimal | None = None

        trading_dates = self._trading_dates(instruments[0].id, start_date, end_date)
        if not trading_dates:
            return {"trade_count": 0, "running_days": 0}

        for idx, trade_date in enumerate(trading_dates):
            bars = self._bars_by_date(instruments, trade_date)
            if not bars:
                continue

            if idx == 1:
                allocation = cash / Decimal(len(instruments))
                for instrument in instruments:
                    bar = bars[instrument.id]
                    quantity = (allocation / bar.open // Decimal("100")) * Decimal("100")
                    if quantity <= 0:
                        continue
                    decision = self.rules.validate(
                        TradeRequest(
                            side="buy",
                            quantity=quantity,
                            price=bar.open,
                            available_cash=cash,
                            sellable_quantity=sellable[instrument.id],
                        )
                    )
                    if decision.accepted:
                        fees = self.rules.calculate_fees(
                            "buy",
                            quantity * bar.open,
                            portfolio.commission_rate,
                            portfolio.stamp_tax_rate,
                            portfolio.slippage_rate,
                        )
                        gross = quantity * bar.open
                        net = gross + fees["commission"] + fees["slippage"]
                        cash -= net
                        holdings[instrument.id] += quantity
                        costs[instrument.id] += net
                        trade_count += 1
                        signal = self._create_signal(portfolio.id, instrument.id, trade_date, "buy", bar.close)
                        self._create_trade(
                            portfolio.id,
                            instrument.id,
                            signal.id,
                            trade_date,
                            "buy",
                            quantity,
                            bar.open,
                            gross,
                            fees,
                            net,
                        )
                        self._create_cash_flow(
                            portfolio.id,
                            trade_date,
                            "buy",
                            -net,
                            cash,
                            Decimal("0"),
                            cash,
                        )

            if idx > 0:
                sellable = holdings.copy()

            position_value = Decimal("0")
            for instrument in instruments:
                bar = bars[instrument.id]
                quantity = holdings[instrument.id]
                market_value = quantity * bar.close
                position_value += market_value
                total_asset_tmp = cash + position_value
                weight = float(market_value / total_asset_tmp) if total_asset_tmp else 0.0
                self.db.add(
                    PortfolioPosition(
                        portfolio_id=portfolio.id,
                        instrument_id=instrument.id,
                        trade_date=trade_date,
                        quantity=quantity,
                        sellable_quantity=sellable[instrument.id],
                        cost_amount=costs[instrument.id],
                        market_value=market_value,
                        weight=weight,
                    )
                )

            total_asset = cash + position_value
            if total_asset >= peak_asset:
                peak_asset = total_asset
                drawdown_start_index = running_days
            drawdown = float((total_asset - peak_asset) / peak_asset) if peak_asset else 0.0
            if drawdown < max_drawdown:
                max_drawdown = drawdown
                max_drawdown_days = running_days - drawdown_start_index
            running_days += 1
            if previous_asset and previous_asset > 0:
                daily_returns.append(float(total_asset / previous_asset - 1))
            previous_asset = total_asset
            net_value = float(total_asset / portfolio.initial_cash)
            annual_return = net_value ** (252 / max(running_days, 1)) - 1
            volatility = pstdev(daily_returns) * (252**0.5) if len(daily_returns) > 1 else 0.0
            sharpe = (mean(daily_returns) / pstdev(daily_returns) * (252**0.5)) if len(daily_returns) > 1 and pstdev(daily_returns) else 0.0
            self.db.add(
                PortfolioMetric(
                    portfolio_id=portfolio.id,
                    metric_date=trade_date,
                    net_value=net_value,
                    total_return=net_value - 1,
                    annual_return=annual_return,
                    win_rate=1.0 if trade_count else 0.0,
                    profit_loss_ratio=0.0,
                    sharpe_ratio=sharpe,
                    current_drawdown=drawdown,
                    max_drawdown=max_drawdown,
                    max_drawdown_days=max_drawdown_days,
                    volatility=volatility,
                    sqn=trade_count**0.5 if trade_count else 0.0,
                    vwr=annual_return / abs(max_drawdown) if max_drawdown else 0.0,
                    trade_count=trade_count,
                    running_days=running_days,
                    created_at=utc_now(),
                )
            )

        return {"trade_count": trade_count, "running_days": running_days}

    def _trading_dates(self, instrument_id: int, start_date: date, end_date: date) -> list[date]:
        rows = (
            self.db.query(MarketDailyBar.trade_date)
            .filter(
                MarketDailyBar.instrument_id == instrument_id,
                MarketDailyBar.trade_date >= start_date,
                MarketDailyBar.trade_date <= end_date,
            )
            .order_by(MarketDailyBar.trade_date)
            .all()
        )
        return [row[0] for row in rows]

    def _bars_by_date(self, instruments: list[Instrument], trade_date: date) -> dict[int, MarketDailyBar]:
        rows = (
            self.db.query(MarketDailyBar)
            .filter(
                MarketDailyBar.instrument_id.in_([item.id for item in instruments]),
                MarketDailyBar.trade_date == trade_date,
            )
            .all()
        )
        return {row.instrument_id: row for row in rows}

    def _create_signal(
        self,
        portfolio_id: int,
        instrument_id: int,
        signal_date: date,
        side: str,
        price: Decimal,
    ) -> Signal:
        signal = Signal(
            portfolio_id=portfolio_id,
            instrument_id=instrument_id,
            run_id=None,
            signal_date=signal_date,
            side=side,
            price=price,
            status="traded",
            email_status="pending",
            created_at=utc_now(),
        )
        self.db.add(signal)
        self.db.flush()
        return signal

    def _create_trade(
        self,
        portfolio_id: int,
        instrument_id: int,
        signal_id: int,
        trade_date: date,
        side: str,
        quantity: Decimal,
        price: Decimal,
        gross: Decimal,
        fees: dict[str, Decimal],
        net: Decimal,
    ) -> None:
        self.db.add(
            Trade(
                portfolio_id=portfolio_id,
                instrument_id=instrument_id,
                run_id=None,
                signal_id=signal_id,
                signal_date=trade_date,
                trade_date=trade_date,
                side=side,
                quantity=quantity,
                price=price,
                gross_amount=gross,
                commission=fees["commission"],
                stamp_tax=fees["stamp_tax"],
                slippage=fees["slippage"],
                net_amount=net,
                status="filled",
                created_at=utc_now(),
            )
        )

    def _create_cash_flow(
        self,
        portfolio_id: int,
        flow_date: date,
        flow_type: str,
        amount: Decimal,
        available_cash: Decimal,
        position_value: Decimal,
        total_asset: Decimal,
    ) -> None:
        self.db.add(
            CashFlow(
                portfolio_id=portfolio_id,
                run_id=None,
                flow_date=flow_date,
                flow_type=flow_type,
                amount=amount,
                available_cash=available_cash,
                position_value=position_value,
                total_asset=total_asset,
                created_at=utc_now(),
            )
        )
