from decimal import Decimal, ROUND_HALF_UP


MONEY_QUANT = Decimal("0.01")
PRICE_QUANT = Decimal("0.0001")


def money(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value)).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def price(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value)).quantize(PRICE_QUANT, rounding=ROUND_HALF_UP)

