from datetime import date, timedelta


def is_trading_day(day: date) -> bool:
    return day.weekday() < 5


def next_trading_day(day: date) -> date:
    current = day + timedelta(days=1)
    while not is_trading_day(current):
        current += timedelta(days=1)
    return current

