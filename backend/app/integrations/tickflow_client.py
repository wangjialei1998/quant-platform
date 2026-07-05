from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from typing import Any

from app.core.config import settings


class TickFlowClient:
    """Thin adapter around the TickFlow Python SDK for unadjusted daily bars."""

    def get_instrument(self, symbol: str) -> dict | None:
        client = self._client()
        normalized_symbol = normalize_symbol(symbol)
        try:
            data = client.instruments.get(normalized_symbol)
        except Exception:
            return None
        return data if isinstance(data, dict) else None

    def fetch_daily_bars(self, symbol: str, start_date: date, end_date: date) -> list[dict]:
        if end_date < start_date:
            return []

        client = self._client()
        normalized_symbol = normalize_symbol(symbol)
        try:
            response = client.klines.get(
                normalized_symbol,
                period="1d",
                count=10000,
                start_time=_to_millis(start_date, is_end=False),
                end_time=_to_millis(end_date, is_end=True),
                adjust="none",
                as_dataframe=True,
            )
        except TypeError:
            response = client.klines.get(
                symbol=normalized_symbol,
                period="1d",
                count=10000,
                start_time=_to_millis(start_date, is_end=False),
                end_time=_to_millis(end_date, is_end=True),
                adjust="none",
                as_dataframe=True,
            )
        except Exception as exc:
            raise RuntimeError(f"TickFlow daily bar fetch failed for {normalized_symbol}: {exc}") from exc

        bars: list[dict] = []
        for row in _iter_rows(response):
            parsed = _parse_bar(row)
            if parsed and start_date <= parsed["trade_date"] <= end_date:
                bars.append(parsed)
        bars.sort(key=lambda item: item["trade_date"])
        return bars

    def _client(self) -> Any:
        try:
            from tickflow import TickFlow
        except ImportError as exc:
            raise RuntimeError("TickFlow SDK is not installed. Rebuild the backend image after updating requirements.") from exc

        if not settings.tickflow_api_key:
            raise RuntimeError("TICKFLOW_API_KEY is required for TickFlow market data access.")
        for factory in (
            lambda: TickFlow(api_key=settings.tickflow_api_key),
            lambda: TickFlow(token=settings.tickflow_api_key),
            lambda: TickFlow.pro(settings.tickflow_api_key),
        ):
            try:
                return factory()
            except Exception:
                continue
        raise RuntimeError("TickFlow API-key client initialization failed.")


def normalize_symbol(symbol: str) -> str:
    cleaned = symbol.strip().upper()
    if "." in cleaned:
        code, suffix = cleaned.split(".", 1)
        if suffix == "SSE":
            return f"{code}.SH"
        if suffix == "SZSE":
            return f"{code}.SZ"
        return cleaned
    if cleaned.startswith(("5", "6", "9")):
        return f"{cleaned}.SH"
    return f"{cleaned}.SZ"


def infer_exchange(symbol: str) -> str:
    normalized = normalize_symbol(symbol)
    suffix = normalized.split(".", 1)[1]
    return {"SH": "SSE", "SZ": "SZSE"}.get(suffix, suffix)


def infer_instrument_type(symbol: str) -> str:
    code = normalize_symbol(symbol).split(".", 1)[0]
    if code.startswith(("15", "16", "18", "50", "51", "52", "56", "58")):
        return "etf"
    if code.startswith(("000300", "000905", "399")):
        return "index"
    return "stock"


def _to_millis(day: date, is_end: bool) -> int:
    value_time = time.max if is_end else time.min
    return int(datetime.combine(day, value_time).timestamp() * 1000)


def _iter_rows(response: Any) -> list[Any]:
    if response is None:
        return []
    if hasattr(response, "to_dict"):
        try:
            rows = response.to_dict("records")
            if rows:
                return rows
        except TypeError:
            values = list(response.to_dict().values())
            if values:
                return values
        if hasattr(response, "reset_index"):
            try:
                return response.reset_index().to_dict("records")
            except Exception:
                pass
    for attr in ("data", "items", "bars", "klines", "records"):
        value = getattr(response, attr, None)
        if value is not None:
            return _iter_rows(value)
    if isinstance(response, dict):
        for key in ("data", "items", "bars", "klines", "records"):
            if key in response:
                return _iter_rows(response[key])
        return [response]
    if isinstance(response, (list, tuple)):
        return list(response)
    return []


def _parse_bar(row: Any) -> dict | None:
    if hasattr(row, "_asdict"):
        row = row._asdict()
    if not isinstance(row, dict):
        row = {
            key: getattr(row, key)
            for key in dir(row)
            if not key.startswith("_") and not callable(getattr(row, key))
        }

    trade_date = _date_value(_first_value(row, "trade_date", "date", "day", "time", "datetime", "timestamp"))
    open_price = _decimal_value(_first_value(row, "open", "open_price", "o"))
    high = _decimal_value(_first_value(row, "high", "high_price", "h"))
    low = _decimal_value(_first_value(row, "low", "low_price", "l"))
    close = _decimal_value(_first_value(row, "close", "close_price", "c"))
    if not trade_date or open_price is None or high is None or low is None or close is None:
        return None

    return {
        "trade_date": trade_date,
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "volume": _decimal_value(_first_value(row, "volume", "vol", "v")),
        "amount": _decimal_value(_first_value(row, "amount", "turnover", "money")),
        "limit_up": _decimal_value(_first_value(row, "limit_up", "up_limit")),
        "limit_down": _decimal_value(_first_value(row, "limit_down", "down_limit")),
        "is_suspended": bool(_first_value(row, "is_suspended", "suspended") or False),
    }


def _first_value(row: dict, *keys: str) -> Any:
    lower_map = {str(key).lower(): value for key, value in row.items()}
    for key in keys:
        if key in row:
            return row[key]
        lowered = key.lower()
        if lowered in lower_map:
            return lower_map[lowered]
    return None


def _date_value(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, (int, float)):
        seconds = value / 1000 if value > 10_000_000_000 else value
        return datetime.fromtimestamp(seconds).date()
    text = str(value).strip()
    if not text:
        return None
    candidates = (
        (text[:10], "%Y-%m-%d"),
        (text[:8], "%Y%m%d"),
        (text[:19], "%Y-%m-%d %H:%M:%S"),
    )
    for candidate, fmt in candidates:
        try:
            return datetime.strptime(candidate, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _decimal_value(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
