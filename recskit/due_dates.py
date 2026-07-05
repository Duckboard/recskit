"""
recskit.due_dates
==================
Calculates an invoice's due date from its invoice date and a supplier's
(or customer's) payment terms. Different trading partners quote terms
in different ways -- "30 days", "29 days from the end of the month
following", "last day of the month after invoice month" -- and getting
this wrong is exactly what makes an "overdue" flag either useless
(triggers too early) or dangerous (triggers too late).
"""

from datetime import date, timedelta

# The four due-date conventions this covers. If a trading partner uses
# something not listed here, "invoice_date" (a flat N days from the
# invoice date) is the safest fallback -- it's the most common by far.
DUE_FROM_MODES = (
    "invoice_date",
    "start_of_following_month",
    "end_of_month",
    "end_of_following_month",
)


def _last_day_of_month(year: int, month: int) -> date:
    if month == 12:
        return date(year, 12, 31)
    return date(year, month + 1, 1) - timedelta(days=1)


def calc_due_date(invoice_date: date, terms_days: int, due_from: str = "invoice_date") -> date:
    """
    Calculate an invoice's due date.

    due_from options:
        "invoice_date"             -- N days from the invoice date
                                       (the default, and most common)
        "start_of_following_month" -- N days from the 1st of the month
                                       after the invoice date, e.g.
                                       "29 days" meaning the 30th of
                                       the month after next
        "end_of_month"             -- N days from the last day of the
                                       invoice's own month, e.g.
                                       "14 days EOM"
        "end_of_following_month"   -- the last day of the month AFTER
                                       the invoice month, no day offset
                                       (terms_days is ignored for this
                                       mode -- it's a fixed rule, e.g.
                                       "last day of the month following
                                       the invoice")

    Raises ValueError for an unrecognised due_from value, rather than
    silently falling back to a default -- an unnoticed typo here would
    quietly miscalculate every due date for that trading partner.
    """
    if due_from not in DUE_FROM_MODES:
        raise ValueError(f"Unknown due_from {due_from!r} -- must be one of {DUE_FROM_MODES}")

    if due_from == "start_of_following_month":
        if invoice_date.month == 12:
            first_next = date(invoice_date.year + 1, 1, 1)
        else:
            first_next = date(invoice_date.year, invoice_date.month + 1, 1)
        return first_next + timedelta(days=terms_days)

    if due_from == "end_of_month":
        return _last_day_of_month(invoice_date.year, invoice_date.month) + timedelta(days=terms_days)

    if due_from == "end_of_following_month":
        if invoice_date.month == 12:
            target_year, target_month = invoice_date.year + 1, 1
        else:
            target_year, target_month = invoice_date.year, invoice_date.month + 1
        return _last_day_of_month(target_year, target_month)

    # "invoice_date"
    return invoice_date + timedelta(days=terms_days)
