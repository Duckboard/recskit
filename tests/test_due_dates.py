from datetime import date

import pytest

from recskit.due_dates import calc_due_date


def test_invoice_date_default():
    assert calc_due_date(date(2026, 5, 14), 30) == date(2026, 6, 13)


def test_start_of_following_month():
    # Invoice 14/05 + 29 days from 1st of following month (June) -> 30/06
    assert calc_due_date(date(2026, 5, 14), 29, "start_of_following_month") == date(2026, 6, 30)


def test_start_of_following_month_december_wraps_year():
    assert calc_due_date(date(2026, 12, 10), 10, "start_of_following_month") == date(2027, 1, 11)


def test_end_of_month():
    # 14 days EOM: invoice 03/05 -> end of May (31st) + 14 days
    assert calc_due_date(date(2026, 5, 3), 14, "end_of_month") == date(2026, 6, 14)


def test_end_of_following_month():
    # Last day of the month AFTER the invoice month, terms_days ignored
    assert calc_due_date(date(2026, 5, 3), 999, "end_of_following_month") == date(2026, 6, 30)


def test_end_of_following_month_december_wraps_year():
    assert calc_due_date(date(2026, 12, 5), 0, "end_of_following_month") == date(2027, 1, 31)


def test_unknown_due_from_raises():
    with pytest.raises(ValueError):
        calc_due_date(date(2026, 5, 1), 30, "next_full_moon")
