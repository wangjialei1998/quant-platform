from datetime import date, timedelta


def _date_range(start: date, end: date) -> set[date]:
    current = start
    days: set[date] = set()
    while current <= end:
        days.add(current)
        current += timedelta(days=1)
    return days


# A-share market holidays published by SSE. Weekends are closed even when
# they are official make-up workdays.
CN_MARKET_HOLIDAYS: set[date] = set().union(
    _date_range(date(2024, 1, 1), date(2024, 1, 1)),
    _date_range(date(2024, 2, 9), date(2024, 2, 17)),
    _date_range(date(2024, 4, 4), date(2024, 4, 6)),
    _date_range(date(2024, 5, 1), date(2024, 5, 5)),
    _date_range(date(2024, 6, 10), date(2024, 6, 10)),
    _date_range(date(2024, 9, 15), date(2024, 9, 17)),
    _date_range(date(2024, 10, 1), date(2024, 10, 7)),
    _date_range(date(2025, 1, 1), date(2025, 1, 1)),
    _date_range(date(2025, 1, 28), date(2025, 2, 4)),
    _date_range(date(2025, 4, 4), date(2025, 4, 6)),
    _date_range(date(2025, 5, 1), date(2025, 5, 5)),
    _date_range(date(2025, 5, 31), date(2025, 6, 2)),
    _date_range(date(2025, 10, 1), date(2025, 10, 8)),
    _date_range(date(2026, 1, 1), date(2026, 1, 3)),
    _date_range(date(2026, 2, 15), date(2026, 2, 23)),
    _date_range(date(2026, 4, 4), date(2026, 4, 6)),
    _date_range(date(2026, 5, 1), date(2026, 5, 5)),
    _date_range(date(2026, 6, 19), date(2026, 6, 21)),
    _date_range(date(2026, 9, 25), date(2026, 9, 27)),
    _date_range(date(2026, 10, 1), date(2026, 10, 7)),
)


def is_trading_day(day: date) -> bool:
    return day.weekday() < 5 and day not in CN_MARKET_HOLIDAYS


def next_or_same_trading_day(day: date) -> date:
    current = day
    while not is_trading_day(current):
        current += timedelta(days=1)
    return current


def previous_or_same_trading_day(day: date) -> date:
    current = day
    while not is_trading_day(current):
        current -= timedelta(days=1)
    return current


def next_trading_day(day: date) -> date:
    current = day + timedelta(days=1)
    while not is_trading_day(current):
        current += timedelta(days=1)
    return current


def previous_trading_day(day: date) -> date:
    current = day - timedelta(days=1)
    while not is_trading_day(current):
        current -= timedelta(days=1)
    return current


def trading_day_count(start_date: date, end_date: date) -> int:
    if end_date < start_date:
        return 0

    current = start_date
    count = 0
    while current <= end_date:
        if is_trading_day(current):
            count += 1
        current += timedelta(days=1)
    return count
