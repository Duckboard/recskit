from datetime import date

from recskit.matching import find_best_name_match, match_invoice, match_payment, normalize_name
from recskit.models import LedgerInvoice, LedgerPayment, StatementItem


def test_normalize_name_strips_punctuation_and_uppercases():
    assert normalize_name("N.D. John") == normalize_name("ND John") == "NDJOHN"


def test_match_invoice_exact_ref():
    item = StatementItem(type="invoice", ref="INV-100", amount=500.0, date=date(2026, 5, 1))
    ledger = [LedgerInvoice(ref="INV-100", amount=500.0, date=date(2026, 5, 1), outstanding=500.0)]

    result = match_invoice(item, ledger)
    assert result.status == "ok"
    assert result.ledger_ref == "INV-100"


def test_match_invoice_uses_alt_ref():
    item = StatementItem(type="invoice", ref="FBEH2328", alt_ref="FBIH4586", amount=371.64)
    ledger = [LedgerInvoice(ref="FBIH4586", amount=371.64)]

    result = match_invoice(item, ledger)
    assert result.status == "ok"
    assert result.ledger_ref == "FBIH4586"


def test_match_invoice_mismatch_amount():
    item = StatementItem(type="invoice", ref="INV-101", amount=320.0)
    ledger = [LedgerInvoice(ref="INV-101", amount=300.0)]

    result = match_invoice(item, ledger)
    assert result.status == "mismatch"
    assert result.ledger_amount == 300.0


def test_match_invoice_missing():
    item = StatementItem(type="invoice", ref="INV-999", amount=100.0)
    result = match_invoice(item, [LedgerInvoice(ref="INV-100", amount=500.0)])
    assert result.status == "missing"


def test_match_invoice_prefers_exact_over_substring():
    """
    The core regression this guards against: a short ref ("991") that is
    also a substring of an unrelated, older invoice's ref ("INV-99910")
    must NOT be paired with that unrelated invoice if an exact match
    exists elsewhere. Exact match wins even though substring matching
    would also "succeed" (on the wrong invoice).
    """
    item = StatementItem(type="invoice", ref="991", amount=50.0)
    ledger = [
        LedgerInvoice(ref="INV-99910", amount=99999.0),  # substring trap
        LedgerInvoice(ref="991", amount=50.0),  # the real match
    ]

    result = match_invoice(item, ledger)
    assert result.status == "ok"
    assert result.ledger_ref == "991"


def test_match_invoice_falls_back_to_substring_when_no_exact_match():
    item = StatementItem(type="invoice", ref="99910", amount=123.45)
    ledger = [LedgerInvoice(ref="INV-99910", amount=123.45)]

    result = match_invoice(item, ledger)
    assert result.status == "ok"
    assert result.ledger_ref == "INV-99910"


def test_match_payment_by_amount():
    item = StatementItem(type="payment", ref="bacs", amount=300.0)
    ledger = [LedgerPayment(ref="BACS-9001", amount=300.0)]

    result = match_payment(item, ledger)
    assert result.status == "ok"
    assert result.ledger_ref == "BACS-9001"


def test_match_payment_falls_back_to_ref_when_amount_differs():
    item = StatementItem(type="payment", ref="REF123", amount=300.0)
    ledger = [LedgerPayment(ref="X-REF123-Y", amount=299.0)]

    result = match_payment(item, ledger)
    assert result.status == "ok"
    assert result.ledger_ref == "X-REF123-Y"


def test_match_payment_missing():
    item = StatementItem(type="payment", ref="bacs", amount=300.0)
    result = match_payment(item, [LedgerPayment(ref="OTHER", amount=999.0)])
    assert result.status == "missing"


def test_find_best_name_match_single():
    candidates = [("A1", "Northwind Beverages Ltd")]
    assert find_best_name_match("Northwind", candidates) == ("A1", "Northwind Beverages Ltd")


def test_find_best_name_match_uses_tie_breaker():
    candidates = [("A1", "Northwind Drinks"), ("A2", "Northwind Drinks Wholesale")]
    result = find_best_name_match("Northwind", candidates, tie_breaker_counts={"A1": 3, "A2": 10})
    assert result[0] == "A2"


def test_find_best_name_match_none():
    assert find_best_name_match("Nonexistent", [("A1", "Something Else")]) is None
