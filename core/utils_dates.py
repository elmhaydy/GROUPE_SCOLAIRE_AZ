# core/utils_dates.py
from __future__ import annotations
from datetime import date

def month_start(d: date) -> date:
    return d.replace(day=1)

def add_months(d: date, months: int) -> date:
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    day = min(d.day, 28)  # safe simple (tu peux améliorer)
    return date(y, m, day)
