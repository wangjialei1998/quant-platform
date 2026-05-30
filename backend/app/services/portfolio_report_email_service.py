from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from html import escape

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.integrations.smtp_client import SMTPClient
from app.models.instrument import Instrument
from app.models.market_data import MarketDailyBar
from app.models.metric import PortfolioMetric
from app.models.portfolio import Portfolio, PortfolioInstrument, PortfolioPosition
from app.models.signal import Signal
from app.models.trade import Trade
from app.services.notification_service import NotificationService


@dataclass(frozen=True)
class PortfolioEmailReport:
    subject: str
    plain_text: str
    html: str
    should_send: bool


class PortfolioReportEmailService:
    def __init__(self, db: Session):
        self.db = db

    def create_report_notification(
        self,
        portfolio: Portfolio,
        run_id: int | None = None,
        force: bool = True,
        title_prefix: str | None = None,
        report_date: date | None = None,
    ) -> int | None:
        report = self.build_report(
            portfolio.id,
            run_id=run_id,
            force=force,
            title_prefix=title_prefix,
            report_date=report_date,
        )
        if not report.should_send:
            return None
        notification = NotificationService(self.db).create_event(
            portfolio,
            "daily_report",
            report.subject,
            report.html,
            should_send=True,
        )
        return notification.id

    def send_report_now(
        self,
        portfolio_id: int,
        run_id: int | None = None,
        force: bool = True,
        title_prefix: str | None = "测试",
        report_date: date | None = None,
    ) -> PortfolioEmailReport:
        report = self.build_report(
            portfolio_id,
            run_id=run_id,
            force=force,
            title_prefix=title_prefix,
            report_date=report_date,
        )
        if not report.should_send:
            raise RuntimeError("Report was skipped")
        SMTPClient().send(report.subject, report.plain_text, html_body=report.html)
        return report

    def build_report(
        self,
        portfolio_id: int,
        run_id: int | None = None,
        force: bool = True,
        title_prefix: str | None = None,
        report_date: date | None = None,
    ) -> PortfolioEmailReport:
        portfolio = self.db.get(Portfolio, portfolio_id)
        if not portfolio:
            raise RuntimeError("Portfolio not found")

        latest_metric = self._metric_for_report_date(portfolio_id, report_date)
        actual_report_date = latest_metric.metric_date if latest_metric else report_date or date.today()
        previous_metric = self._previous_metric(portfolio_id, actual_report_date) if latest_metric else None
        day_signals = self._signals_for_report_day(portfolio_id, actual_report_date, run_id)
        day_trades = self._trades_for_report_day(portfolio_id, actual_report_date, run_id)

        portfolio_instruments = self._portfolio_instruments(portfolio_id)
        positions = self._positions_for_report_day(portfolio_id, actual_report_date)
        held_rows = self._held_rows(portfolio, positions, actual_report_date)
        held_instrument_ids = {item["instrument_id"] for item in held_rows}
        watch_rows = self._watch_rows(portfolio_id, portfolio_instruments, held_instrument_ids, actual_report_date)

        total_asset = self._current_total_asset(portfolio, latest_metric)
        previous_asset = self._current_total_asset(portfolio, previous_metric)
        daily_pnl = total_asset - previous_asset if previous_metric else Decimal("0")
        daily_pnl_rate = float(total_asset / previous_asset - 1) if previous_metric and previous_asset else 0.0
        position_value = sum((_decimal(item["market_value"]) for item in held_rows), Decimal("0"))
        position_ratio = float(position_value / total_asset) if total_asset else 0.0

        subject_prefix = f"{title_prefix} " if title_prefix else ""
        subject = f"{subject_prefix}{portfolio.name} 每日量化监控报告 {actual_report_date.isoformat()}"
        html = self._build_html(
            portfolio=portfolio,
            report_date=actual_report_date,
            latest_metric=latest_metric,
            daily_pnl=daily_pnl,
            daily_pnl_rate=daily_pnl_rate,
            total_asset=total_asset,
            position_ratio=position_ratio,
            signals=day_signals,
            trades=day_trades,
            held_rows=held_rows,
            watch_rows=watch_rows,
        )
        plain_text = self._build_plain_text(
            portfolio=portfolio,
            report_date=actual_report_date,
            latest_metric=latest_metric,
            daily_pnl=daily_pnl,
            daily_pnl_rate=daily_pnl_rate,
            total_asset=total_asset,
            position_ratio=position_ratio,
            signals=day_signals,
            held_rows=held_rows,
            watch_rows=watch_rows,
        )
        return PortfolioEmailReport(subject=subject, plain_text=plain_text, html=html, should_send=force)

    def _metric_for_report_date(self, portfolio_id: int, report_date: date | None) -> PortfolioMetric | None:
        query = self.db.query(PortfolioMetric).filter(PortfolioMetric.portfolio_id == portfolio_id)
        if report_date:
            query = query.filter(PortfolioMetric.metric_date <= report_date)
        return query.order_by(PortfolioMetric.metric_date.desc()).first()

    def _previous_metric(self, portfolio_id: int, report_date: date) -> PortfolioMetric | None:
        return (
            self.db.query(PortfolioMetric)
            .filter(PortfolioMetric.portfolio_id == portfolio_id, PortfolioMetric.metric_date < report_date)
            .order_by(PortfolioMetric.metric_date.desc())
            .first()
        )

    def _portfolio_instruments(self, portfolio_id: int) -> list[Instrument]:
        return (
            self.db.query(Instrument)
            .join(PortfolioInstrument, PortfolioInstrument.instrument_id == Instrument.id)
            .filter(PortfolioInstrument.portfolio_id == portfolio_id, Instrument.is_active.is_(True))
            .order_by(Instrument.symbol)
            .all()
        )

    def _positions_for_report_day(self, portfolio_id: int, report_date: date) -> list[tuple[PortfolioPosition, Instrument]]:
        latest_date = (
            self.db.query(func.max(PortfolioPosition.trade_date))
            .filter(
                PortfolioPosition.portfolio_id == portfolio_id,
                PortfolioPosition.trade_date <= report_date,
            )
            .scalar()
        )
        if not latest_date:
            return []
        return (
            self.db.query(PortfolioPosition, Instrument)
            .join(Instrument, Instrument.id == PortfolioPosition.instrument_id)
            .filter(
                PortfolioPosition.portfolio_id == portfolio_id,
                PortfolioPosition.trade_date == latest_date,
            )
            .order_by(Instrument.symbol)
            .all()
        )

    def _signals_for_report_day(
        self,
        portfolio_id: int,
        report_date: date,
        run_id: int | None,
    ) -> list[tuple[Signal, Instrument]]:
        query = (
            self.db.query(Signal, Instrument)
            .join(Instrument, Instrument.id == Signal.instrument_id)
            .filter(Signal.portfolio_id == portfolio_id, Signal.signal_date == report_date)
        )
        if run_id is not None:
            query = query.filter(Signal.run_id == run_id)
        return query.order_by(Instrument.symbol, Signal.id).all()

    def _trades_for_report_day(
        self,
        portfolio_id: int,
        report_date: date,
        run_id: int | None,
    ) -> list[tuple[Trade, Instrument]]:
        query = (
            self.db.query(Trade, Instrument)
            .join(Instrument, Instrument.id == Trade.instrument_id)
            .filter(
                Trade.portfolio_id == portfolio_id,
                Trade.status == "filled",
                or_(Trade.trade_date == report_date, Trade.signal_date == report_date),
            )
        )
        if run_id is not None:
            query = query.filter(Trade.run_id == run_id)
        return query.order_by(Instrument.symbol, Trade.id).all()

    def _held_rows(
        self,
        portfolio: Portfolio,
        positions: list[tuple[PortfolioPosition, Instrument]],
        report_date: date,
    ) -> list[dict]:
        rows = []
        for position, instrument in positions:
            if _decimal(position.quantity) <= 0 or _decimal(position.market_value) <= 0:
                continue
            latest_trade = self._latest_trade(portfolio.id, instrument.id, report_date)
            latest_bar = self._latest_bar(instrument.id, report_date)
            rows.append(
                {
                    "instrument_id": instrument.id,
                    "symbol": instrument.symbol,
                    "name": instrument.name,
                    "quantity": position.quantity,
                    "market_value": position.market_value,
                    "weight": position.weight,
                    "latest_trade_price": latest_trade.price if latest_trade else None,
                    "latest_close": latest_bar.close if latest_bar else None,
                    "price_date": latest_bar.trade_date if latest_bar else None,
                }
            )
        return rows

    def _watch_rows(
        self,
        portfolio_id: int,
        instruments: list[Instrument],
        held_instrument_ids: set[int],
        report_date: date,
    ) -> list[dict]:
        rows = []
        for instrument in instruments:
            if instrument.id in held_instrument_ids:
                continue
            latest_bar = self._latest_bar(instrument.id, report_date)
            last_sell = self._latest_sell_trade(portfolio_id, instrument.id, report_date)
            previous_buy = self._previous_buy_trade(portfolio_id, instrument.id, last_sell) if last_sell else None
            sell_return = None
            if last_sell and previous_buy and _decimal(previous_buy.price) > 0:
                sell_return = float(_decimal(last_sell.price) / _decimal(previous_buy.price) - 1)
            rows.append(
                {
                    "instrument_id": instrument.id,
                    "symbol": instrument.symbol,
                    "name": instrument.name,
                    "current_price": latest_bar.close if latest_bar else None,
                    "price_date": latest_bar.trade_date if latest_bar else None,
                    "current_value": Decimal("0"),
                    "last_sell_date": last_sell.signal_date or last_sell.trade_date if last_sell else None,
                    "sell_return": sell_return,
                    "weight": 0.0,
                }
            )
        return rows

    def _latest_trade(self, portfolio_id: int, instrument_id: int, report_date: date) -> Trade | None:
        return (
            self.db.query(Trade)
            .filter(
                Trade.portfolio_id == portfolio_id,
                Trade.instrument_id == instrument_id,
                Trade.status == "filled",
                Trade.trade_date <= report_date,
            )
            .order_by(Trade.trade_date.desc(), Trade.id.desc())
            .first()
        )

    def _latest_sell_trade(self, portfolio_id: int, instrument_id: int, report_date: date) -> Trade | None:
        return (
            self.db.query(Trade)
            .filter(
                Trade.portfolio_id == portfolio_id,
                Trade.instrument_id == instrument_id,
                Trade.status == "filled",
                Trade.side == "sell",
                Trade.trade_date <= report_date,
            )
            .order_by(Trade.trade_date.desc(), Trade.id.desc())
            .first()
        )

    def _previous_buy_trade(self, portfolio_id: int, instrument_id: int, sell_trade: Trade) -> Trade | None:
        return (
            self.db.query(Trade)
            .filter(
                Trade.portfolio_id == portfolio_id,
                Trade.instrument_id == instrument_id,
                Trade.status == "filled",
                Trade.side == "buy",
                Trade.trade_date <= sell_trade.trade_date,
            )
            .order_by(Trade.trade_date.desc(), Trade.id.desc())
            .first()
        )

    def _latest_bar(self, instrument_id: int, report_date: date) -> MarketDailyBar | None:
        return (
            self.db.query(MarketDailyBar)
            .filter(
                MarketDailyBar.instrument_id == instrument_id,
                MarketDailyBar.trade_date <= report_date,
                MarketDailyBar.adjustment_type == "none",
            )
            .order_by(MarketDailyBar.trade_date.desc())
            .first()
        )

    def _current_total_asset(self, portfolio: Portfolio, metric: PortfolioMetric | None) -> Decimal:
        if not metric:
            return _decimal(portfolio.initial_cash)
        return (_decimal(portfolio.initial_cash) * _decimal(metric.net_value)).quantize(Decimal("0.01"))

    def _build_html(
        self,
        portfolio: Portfolio,
        report_date: date,
        latest_metric: PortfolioMetric | None,
        daily_pnl: Decimal,
        daily_pnl_rate: float,
        total_asset: Decimal,
        position_ratio: float,
        signals: list[tuple[Signal, Instrument]],
        trades: list[tuple[Trade, Instrument]],
        held_rows: list[dict],
        watch_rows: list[dict],
    ) -> str:
        cards = [
            ("当日盈亏", f"{_money(daily_pnl)} / {_percent(daily_pnl_rate)}", _tone(daily_pnl_rate)),
            ("当前净值", _number(latest_metric.net_value if latest_metric else 1.0, 4), "#2563eb"),
            ("年化收益率", _percent(latest_metric.annual_return if latest_metric else 0), _tone(latest_metric.annual_return if latest_metric else 0)),
            ("夏普比率", _number(latest_metric.sharpe_ratio if latest_metric else 0, 2), "#7c3aed"),
            ("当前回撤", _percent(latest_metric.current_drawdown if latest_metric else 0), "#dc2626"),
            ("历史最大回撤", _percent(latest_metric.max_drawdown if latest_metric else 0), "#991b1b"),
            ("总资产", _money(total_asset), "#0f766e"),
            ("当前仓位", _percent(position_ratio), "#ea580c"),
        ]
        signal_rows = self._signal_rows_html(signals, trades)
        holding_rows = self._holding_rows_html(held_rows)
        watch_rows_html = self._watch_rows_html(watch_rows)
        cards_html = _metric_cards(cards)
        return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>{escape(portfolio.name)} 每日量化监控报告</title>
</head>
<body style="margin:0;background:#eef2f7;font-family:Arial,'Microsoft YaHei',sans-serif;color:#172033;">
  <div style="max-width:980px;margin:0 auto;padding:28px 18px;">
    <div style="background:#111827;border-radius:14px;padding:26px 28px;color:#fff;">
      <div style="font-size:13px;letter-spacing:0;color:#93c5fd;">交易日早盘日报</div>
      <h1 style="margin:8px 0 10px;font-size:26px;line-height:1.3;">{escape(portfolio.name)} 组合日报</h1>
      <div style="font-size:14px;color:#d1d5db;">报告日期：{report_date.isoformat()}。每日开盘前发送上一交易日的组合表现、信号和持仓。</div>
    </div>

    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:18px;border-collapse:separate;border-spacing:12px;">
      {cards_html}
    </table>

    {_section('买卖信号', signal_rows, '#2563eb')}
    {_section('当日持仓', holding_rows, '#16a34a')}
    {_section('组合内未持仓标的', watch_rows_html, '#f97316')}

    <div style="font-size:12px;color:#6b7280;margin-top:18px;line-height:1.7;">
      说明：正式任务会在每个交易日开盘前发送上一交易日报。价格使用未复权日线 close；策略信号按收盘后生成，模拟成交按下一交易日开盘价执行。
    </div>
  </div>
</body>
</html>"""

    def _build_plain_text(
        self,
        portfolio: Portfolio,
        report_date: date,
        latest_metric: PortfolioMetric | None,
        daily_pnl: Decimal,
        daily_pnl_rate: float,
        total_asset: Decimal,
        position_ratio: float,
        signals: list[tuple[Signal, Instrument]],
        held_rows: list[dict],
        watch_rows: list[dict],
    ) -> str:
        lines = [
            f"{portfolio.name} 每日量化监控报告",
            f"报告日期：{report_date.isoformat()}",
            f"当日盈亏：{_money(daily_pnl)} / {_percent(daily_pnl_rate)}",
            f"当前净值：{_number(latest_metric.net_value if latest_metric else 1.0, 4)}",
            f"年化收益率：{_percent(latest_metric.annual_return if latest_metric else 0)}",
            f"夏普比率：{_number(latest_metric.sharpe_ratio if latest_metric else 0, 2)}",
            f"当前回撤：{_percent(latest_metric.current_drawdown if latest_metric else 0)}",
            f"历史最大回撤：{_percent(latest_metric.max_drawdown if latest_metric else 0)}",
            f"总资产：{_money(total_asset)}",
            f"当前仓位：{_percent(position_ratio)}",
            "",
            "买卖信号：",
        ]
        for signal, instrument in signals:
            lines.append(f"{instrument.symbol} {instrument.name} {signal.side} {signal.signal_date} {signal.price}")
        lines.append("")
        lines.append("当日持仓：")
        if held_rows:
            for row in held_rows:
                lines.append(
                    f"{row['symbol']} {row['name']} 数量 {row['quantity']} 当前价值 {_money(row['market_value'])} "
                    f"仓位 {_percent(row['weight'])} 最新成交价 {_price(row['latest_trade_price'])}"
                )
        else:
            lines.append("无持仓。")
        lines.append("")
        lines.append("组合内未持仓标的：")
        if watch_rows:
            for row in watch_rows:
                lines.append(
                    f"{row['symbol']} {row['name']} 当前价格 {_price(row['current_price'])} "
                    f"上次卖出信号 {row['last_sell_date'] or '-'} 卖出收益 {_percent(row['sell_return'])} 当前仓位 0.00%"
                )
        else:
            lines.append("无。")
        return "\n".join(lines)

    def _signal_rows_html(
        self,
        signals: list[tuple[Signal, Instrument]],
        trades: list[tuple[Trade, Instrument]],
    ) -> str:
        rows = []
        seen: set[tuple[str, str, date]] = set()
        for signal, instrument in signals:
            key = (instrument.symbol, signal.side, signal.signal_date)
            seen.add(key)
            rows.append(
                "<tr>"
                f"<td style='{_td()}'>{escape(instrument.symbol)}<br><span style='color:#64748b'>{escape(instrument.name)}</span></td>"
                f"<td style='{_td(color=_side_color(signal.side), bold=True)}'>{_side_label(signal.side)}</td>"
                f"<td style='{_td()}'>{signal.signal_date.isoformat()}</td>"
                f"<td style='{_td()}'>{_price(signal.price)}</td>"
                f"<td style='{_td()}'>{_signal_status_label(signal.status)}</td>"
                "</tr>"
            )
        for trade, instrument in trades:
            key = (instrument.symbol, trade.side, trade.signal_date or trade.trade_date)
            if key in seen:
                continue
            rows.append(
                "<tr>"
                f"<td style='{_td()}'>{escape(instrument.symbol)}<br><span style='color:#64748b'>{escape(instrument.name)}</span></td>"
                f"<td style='{_td(color=_side_color(trade.side), bold=True)}'>{_side_label(trade.side)}</td>"
                f"<td style='{_td()}'>{(trade.signal_date or trade.trade_date).isoformat()}</td>"
                f"<td style='{_td()}'>{_price(trade.price)}</td>"
                f"<td style='{_td()}'>已成交 {trade.trade_date.isoformat()}</td>"
                "</tr>"
            )
        return _table(["标的", "方向", "信号日期", "价格", "状态"], "".join(rows))

    def _holding_rows_html(self, held_rows: list[dict]) -> str:
        if not held_rows:
            return "<div style='padding:16px;color:#475569;background:#f8fafc;border-radius:10px;'>当前无持仓。</div>"
        rows = []
        for row in held_rows:
            rows.append(
                "<tr>"
                f"<td style='{_td()}'>{escape(row['symbol'])}<br><span style='color:#64748b'>{escape(row['name'])}</span></td>"
                f"<td style='{_td()}'>{_quantity(row['quantity'])}</td>"
                f"<td style='{_td()}'>{_money(row['market_value'])}</td>"
                f"<td style='{_td(color='#0f766e', bold=True)}'>{_percent(row['weight'])}</td>"
                f"<td style='{_td()}'>{_price(row['latest_trade_price'])}</td>"
                f"<td style='{_td()}'>{_price(row['latest_close'])}<br><span style='color:#64748b'>{row['price_date'] or '-'}</span></td>"
                "</tr>"
            )
        return _table(["标的", "持仓数量", "当前价值", "仓位大小", "最新成交价", "最新收盘价"], "".join(rows))

    def _watch_rows_html(self, watch_rows: list[dict]) -> str:
        if not watch_rows:
            return "<div style='padding:16px;color:#475569;background:#f8fafc;border-radius:10px;'>组合内没有未持仓标的。</div>"
        rows = []
        for row in watch_rows:
            rows.append(
                "<tr>"
                f"<td style='{_td()}'>{escape(row['symbol'])}<br><span style='color:#64748b'>{escape(row['name'])}</span></td>"
                f"<td style='{_td()}'>{_price(row['current_price'])}<br><span style='color:#64748b'>{row['price_date'] or '-'}</span></td>"
                f"<td style='{_td()}'>{_money(row['current_value'])}</td>"
                f"<td style='{_td()}'>{row['last_sell_date'] or '-'}</td>"
                f"<td style='{_td(color=_tone(row['sell_return'] or 0), bold=True)}'>{_percent(row['sell_return'])}</td>"
                f"<td style='{_td()}'>0.00%</td>"
                "</tr>"
            )
        return _table(["标的", "当前价格", "当前价值", "前一卖信号日期", "卖出收益比例", "当前仓位"], "".join(rows))


def _metric_cards(cards: list[tuple[str, str, str]]) -> str:
    rows = []
    for index in range(0, len(cards), 2):
        left = cards[index]
        right = cards[index + 1] if index + 1 < len(cards) else None
        rows.append("<tr>" + _metric_card_cell(*left) + (_metric_card_cell(*right) if right else "<td></td>") + "</tr>")
    return "\n".join(rows)


def _metric_card_cell(title: str, value: str, color: str) -> str:
    return (
        f"<td style='width:50%;padding:0 6px 12px 0;vertical-align:top;'>"
        f"<div style='background:#fff;border-radius:12px;border-left:5px solid {color};padding:16px;box-shadow:0 8px 20px rgba(15,23,42,.06);'>"
        f"<div style='font-size:13px;color:#64748b;margin-bottom:8px;'>{escape(title)}</div>"
        f"<div style='font-size:22px;line-height:1.2;font-weight:700;color:{color};'>{escape(value)}</div>"
        "</div></td>"
    )


def _section(title: str, content: str, color: str) -> str:
    return (
        f"<div style='background:#fff;border-radius:14px;margin-top:18px;padding:20px 22px;box-shadow:0 8px 20px rgba(15,23,42,.06);'>"
        f"<div style='display:block;border-left:5px solid {color};padding-left:12px;margin-bottom:14px;'>"
        f"<h2 style='margin:0;font-size:18px;line-height:1.3;color:#111827;'>{escape(title)}</h2>"
        "</div>"
        f"{content}"
        "</div>"
    )


def _table(headers: list[str], rows: str) -> str:
    header_html = "".join(f"<th style='{_th()}'>{escape(header)}</th>" for header in headers)
    if not rows:
        rows = f"<tr><td colspan='{len(headers)}' style='{_td(color='#94a3b8')}'> </td></tr>"
    return (
        "<table width='100%' cellpadding='0' cellspacing='0' style='border-collapse:collapse;border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;'>"
        f"<thead><tr>{header_html}</tr></thead>"
        f"<tbody>{rows}</tbody>"
        "</table>"
    )


def _th() -> str:
    return "background:#f8fafc;color:#334155;text-align:left;font-size:13px;padding:11px 10px;border-bottom:1px solid #e5e7eb;"


def _td(color: str = "#111827", bold: bool = False) -> str:
    weight = "700" if bold else "400"
    return f"color:{color};font-weight:{weight};font-size:13px;padding:11px 10px;border-bottom:1px solid #eef2f7;vertical-align:top;"


def _side_label(side: str) -> str:
    return "买入" if side == "buy" else "卖出" if side == "sell" else side


def _side_color(side: str) -> str:
    return "#16a34a" if side == "buy" else "#dc2626" if side == "sell" else "#334155"


def _signal_status_label(status: str) -> str:
    return {"traded": "已成交", "pending_trade": "待次日成交", "rejected": "已拒绝"}.get(status, status)


def _tone(value: float | Decimal | None) -> str:
    return "#16a34a" if _float(value) >= 0 else "#dc2626"


def _money(value: Decimal | float | int | str | None) -> str:
    number = _decimal(value)
    return f"¥{number:,.2f}"


def _price(value: Decimal | float | int | str | None) -> str:
    if value is None:
        return "-"
    return f"{_decimal(value):,.4f}"


def _quantity(value: Decimal | float | int | str | None) -> str:
    return f"{_decimal(value):,.0f}"


def _percent(value: float | Decimal | None) -> str:
    if value is None:
        return "-"
    return f"{_float(value) * 100:.2f}%"


def _number(value: float | Decimal | None, digits: int) -> str:
    if value is None:
        return "-"
    return f"{_float(value):.{digits}f}"


def _decimal(value: Decimal | float | int | str | None) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _float(value: float | Decimal | None) -> float:
    if value is None:
        return 0.0
    return float(value)
