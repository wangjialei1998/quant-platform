from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class TradeRequest:
    side: str
    quantity: Decimal
    price: Decimal
    available_cash: Decimal
    sellable_quantity: Decimal
    is_suspended: bool = False
    is_limit_up: bool = False
    is_limit_down: bool = False


@dataclass(frozen=True)
class TradeDecision:
    accepted: bool
    reason: str | None = None


class TradingRules:
    lot_size = Decimal("100")

    def validate(self, request: TradeRequest) -> TradeDecision:
        if request.is_suspended:
            return TradeDecision(False, "停牌日不可成交")
        if request.quantity <= 0:
            return TradeDecision(False, "交易数量必须大于 0")
        if request.quantity % self.lot_size != 0:
            return TradeDecision(False, "交易数量必须为 100 股整数手")
        if request.side == "buy":
            if request.is_limit_up:
                return TradeDecision(False, "涨停日默认不可买入")
            if request.quantity * request.price > request.available_cash:
                return TradeDecision(False, "可用资金不足")
        if request.side == "sell":
            if request.is_limit_down:
                return TradeDecision(False, "跌停日默认不可卖出")
            if request.quantity > request.sellable_quantity:
                return TradeDecision(False, "可卖持仓不足")
        return TradeDecision(True)

    def calculate_fees(
        self,
        side: str,
        gross_amount: Decimal,
        commission_rate: Decimal,
        stamp_tax_rate: Decimal,
        slippage_rate: Decimal,
    ) -> dict[str, Decimal]:
        commission = gross_amount * commission_rate
        stamp_tax = gross_amount * stamp_tax_rate if side == "sell" else Decimal("0")
        slippage = gross_amount * slippage_rate
        return {
            "commission": commission,
            "stamp_tax": stamp_tax,
            "slippage": slippage,
        }

