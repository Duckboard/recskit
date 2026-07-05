from datetime import date

import pytest

from conftest import FakeCursor
from recskit.sage_adapter import find_purchase_ledger_account, pull_purchase_ledger


def test_find_purchase_ledger_account_single_match():
    cursor = FakeCursor(
        [
            ("FROM PURCHASE_LEDGER", [("A100", "Northwind Beverages Ltd")]),
        ]
    )
    ref, name = find_purchase_ledger_account(cursor, "Northwind")
    assert ref == "A100"
    assert name == "Northwind Beverages Ltd"


def test_find_purchase_ledger_account_ignores_punctuation():
    cursor = FakeCursor(
        [
            ("FROM PURCHASE_LEDGER", [("A200", "N.D. John & Sons")]),
        ]
    )
    ref, name = find_purchase_ledger_account(cursor, "ND John Sons")
    assert ref == "A200"


def test_find_purchase_ledger_account_no_match_raises():
    cursor = FakeCursor([("FROM PURCHASE_LEDGER", [("A100", "Somebody Else Ltd")])])
    with pytest.raises(LookupError):
        find_purchase_ledger_account(cursor, "Nonexistent Supplier")


def test_find_purchase_ledger_account_multiple_matches_uses_transaction_count():
    # Two accounts both match "Northwind" -- pick whichever has more
    # PI/PC/PP transactions (a fake proxy for "the account actually in use").
    cursor = FakeCursor(
        [
            ("FROM PURCHASE_LEDGER", [("A1", "Northwind Old Account"), ("A2", "Northwind Beverages Ltd")]),
            ("'A1'", [(2,)]),
            ("'A2'", [(40,)]),
        ]
    )
    ref, name = find_purchase_ledger_account(cursor, "Northwind")
    assert ref == "A2"
    assert name == "Northwind Beverages Ltd"


def test_pull_purchase_ledger_converts_negative_amounts_to_positive():
    cursor = FakeCursor(
        [
            (
                "('PI', 'PC')",
                [("INV-100", date(2026, 5, 1), 500.00, -500.00), ("INV-101", date(2026, 5, 10), 0.00, -300.00)],
            ),
            ("TYPE = 'PP'", [("BACS-9001", date(2026, 5, 15), -300.00)]),
        ]
    )

    invoices, payments = pull_purchase_ledger(cursor, "A100")

    assert len(invoices) == 2
    assert invoices[0].ref == "INV-100"
    assert invoices[0].amount == 500.00
    assert invoices[0].outstanding == 500.00
    assert invoices[1].outstanding == 0.00

    assert len(payments) == 1
    assert payments[0].ref == "BACS-9001"
    assert payments[0].amount == 300.00
