"""
recskit.reconcile
==================
Ties matching.py and models.py together into one call: hand over a
statement's line items plus your ledger's invoices and payments for
that account, get back a ReconciliationResult with every line matched,
mismatched, or flagged missing, plus a balance comparison.

This module doesn't care where the statement or ledger data came from
-- CSV, a PDF you parsed by hand, Sage, Xero, QuickBooks, whatever.
See recskit.sage_adapter for one concrete way to get ledger data out of
Sage 50, or write your own equivalent for another system.
"""

from typing import List, Optional

from .matching import match_invoice, match_payment
from .models import LedgerInvoice, LedgerPayment, ReconciliationResult, StatementItem


def reconcile_statement(
    items: List[StatementItem],
    ledger_invoices: List[LedgerInvoice],
    ledger_payments: List[LedgerPayment],
    statement_balance: float,
    ledger_balance: Optional[float] = None,
    balance_tolerance: float = 0.02,
) -> ReconciliationResult:
    """
    Reconcile one statement against your ledger.

    `ledger_balance` defaults to the sum of `outstanding` across
    `ledger_invoices` if not supplied directly -- pass it explicitly if
    your ledger's outstanding figure needs to come from somewhere else.

    An item only counts as a discrepancy (invoice/credit-note or
    payment) if it's "mismatch" or "missing" -- an exact match is never
    counted, no matter which fallback path found it.
    """
    doc_items = [i for i in items if i.type in ("invoice", "credit_note")]
    payment_items = [i for i in items if i.type == "payment"]

    invoice_results = [match_invoice(item, ledger_invoices) for item in doc_items]
    payment_results = [match_payment(item, ledger_payments) for item in payment_items]

    if ledger_balance is None:
        ledger_balance = sum(inv.outstanding for inv in ledger_invoices)

    # Ledger invoices that don't appear (even as a substring match) on
    # any statement line -- usually older items sitting in a brought-
    # forward balance, but worth surfacing rather than silently ignoring.
    stmt_refs = {i.ref.upper() for i in doc_items}
    extra_in_ledger = [
        inv for inv in ledger_invoices if not any(r in inv.ref.upper() for r in stmt_refs)
    ]

    balance_difference = round(ledger_balance - statement_balance, 2)

    issue_count = sum(1 for r in invoice_results + payment_results if r.status != "ok")
    balance_ok = abs(balance_difference) < balance_tolerance
    if not balance_ok:
        issue_count += 1

    return ReconciliationResult(
        invoice_results=invoice_results,
        payment_results=payment_results,
        extra_in_ledger=extra_in_ledger,
        statement_balance=statement_balance,
        ledger_balance=ledger_balance,
        balance_difference=balance_difference,
        issue_count=issue_count,
        agreed=(issue_count == 0),
    )
