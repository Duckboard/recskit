from datetime import date

import pytest

from recskit.models import LedgerInvoice, LedgerPayment, StatementItem
from recskit.reconcile import reconcile_statement


def _sample_ledger():
    invoices = [
        LedgerInvoice(ref="INV-100", amount=500.00, date=date(2026, 5, 1), outstanding=500.00),
        LedgerInvoice(ref="INV-101", amount=300.00, date=date(2026, 5, 10), outstanding=300.00),
        LedgerInvoice(ref="INV-102", amount=263.45, date=date(2026, 5, 20), outstanding=263.45),
    ]
    payments = [LedgerPayment(ref="BACS-9001", amount=300.00, date=date(2026, 5, 15))]
    return invoices, payments


def test_all_agree():
    items = [
        StatementItem(type="invoice", ref="INV-100", amount=500.00),
        StatementItem(type="invoice", ref="INV-101", amount=300.00),
        StatementItem(type="invoice", ref="INV-102", amount=263.45),
        StatementItem(type="payment", ref="bacs", amount=300.00),
    ]
    invoices, payments = _sample_ledger()

    result = reconcile_statement(items, invoices, payments, statement_balance=1063.45)

    assert result.agreed
    assert result.issue_count == 0
    assert result.extra_in_ledger == []
    assert result.balance_difference == 0.0


def test_mismatch_and_missing_flagged_even_if_balance_ties():
    """
    Mirrors a real scenario: the statement's printed total can equal
    the ledger's outstanding total even though individual lines don't
    match -- compensating errors. The balance agreeing is not enough;
    every line must be checked.
    """
    items = [
        StatementItem(type="invoice", ref="INV-100", amount=500.00),
        StatementItem(type="invoice", ref="INV-101", amount=320.00),  # mismatch: ledger has 300
        StatementItem(type="invoice", ref="INV-103", amount=150.00),  # missing from ledger
        StatementItem(type="payment", ref="bacs", amount=300.00),
    ]
    invoices, payments = _sample_ledger()  # outstanding totals to 1063.45

    result = reconcile_statement(items, invoices, payments, statement_balance=1063.45)

    assert not result.agreed
    assert result.issue_count == 2  # one mismatch + one missing
    assert result.balance_difference == 0.0  # balance still ties despite the issues
    assert len(result.mismatched_items) == 1
    assert len(result.missing_items) == 1
    # INV-102 is in the ledger but never referenced by any statement line
    assert [inv.ref for inv in result.extra_in_ledger] == ["INV-102"]


def test_balance_difference_flagged_as_issue():
    items = [StatementItem(type="invoice", ref="INV-100", amount=500.00)]
    invoices = [LedgerInvoice(ref="INV-100", amount=500.00, outstanding=500.00)]

    result = reconcile_statement(items, invoices, [], statement_balance=450.00)

    assert not result.agreed
    assert result.balance_difference == 50.00
    assert result.issue_count == 1


def test_balance_within_tolerance_not_flagged():
    items = [StatementItem(type="invoice", ref="INV-100", amount=500.00)]
    invoices = [LedgerInvoice(ref="INV-100", amount=500.00, outstanding=500.00)]

    result = reconcile_statement(items, invoices, [], statement_balance=500.005)

    assert result.agreed
    assert result.issue_count == 0


def test_explicit_ledger_balance_overrides_default():
    items = []
    invoices = [LedgerInvoice(ref="INV-1", amount=100.0, outstanding=100.0)]

    result = reconcile_statement(items, invoices, [], statement_balance=250.0, ledger_balance=250.0)

    assert result.ledger_balance == 250.0
    assert result.agreed
