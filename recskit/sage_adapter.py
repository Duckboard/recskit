"""
recskit.sage_adapter
=====================
Optional adapter that pulls a purchase-ledger account's invoices,
credit notes, and payments out of Sage 50 (via sagekit) and converts
them into recskit's LedgerInvoice / LedgerPayment shapes, ready for
reconcile_statement().

This is one concrete data source -- recskit's reconciliation logic
itself doesn't know or care where the ledger side came from. If you're
on Xero, QuickBooks, or anything else, write your own equivalent that
returns the same two lists; everything downstream is unchanged.

Requires the optional "sage" extra:

    pip install recskit[sage]

or install sagekit directly -- see its own README for the Sage 50
ODBC connection details (DSN, credentials, column auto-detection).
"""

import re
from typing import List, Tuple

from .models import LedgerInvoice, LedgerPayment


def _normalize_name(name: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (name or "").upper())


def find_purchase_ledger_account(cursor, search_term: str) -> Tuple[str, str]:
    """
    Find a supplier account in Sage's PURCHASE_LEDGER by a fuzzy name
    match (ignoring punctuation/spacing, since account names aren't
    entered consistently). If more than one account matches, picks the
    one with the most PI/PC/PP transactions.

    Returns (account_ref, account_name). Raises LookupError if nothing
    matches.
    """
    cursor.execute("SELECT ACCOUNT_REF, NAME FROM PURCHASE_LEDGER")
    all_accounts = cursor.fetchall()

    norm_search = _normalize_name(search_term)
    matches = [a for a in all_accounts if norm_search in _normalize_name(a[1])]

    if not matches:
        raise LookupError(f"No PURCHASE_LEDGER account matching {search_term!r}")

    if len(matches) == 1:
        return matches[0][0], matches[0][1]

    best, best_count = matches[0], -1
    for account_ref, name in matches:
        safe = account_ref.replace("'", "''")
        cursor.execute(
            f"""
            SELECT COUNT(*) FROM AUDIT_HEADER
            WHERE ACCOUNT_REF = '{safe}'
              AND TYPE IN ('PI', 'PC', 'PP')
              AND DELETED_FLAG = 0
            """
        )
        count = cursor.fetchone()[0]
        if count > best_count:
            best_count = count
            best = (account_ref, name)

    return best[0], best[1]


def pull_purchase_ledger(
    cursor, account_ref: str
) -> Tuple[List[LedgerInvoice], List[LedgerPayment]]:
    """
    Pull outstanding invoices/credit notes (type PI/PC) and payments
    (type PP) for a Sage purchase ledger account, converted to
    recskit's LedgerInvoice / LedgerPayment dataclasses.

    Amounts come back from Sage's ODBC layer as negative for purchase
    transactions -- this converts them to positive, matching the
    convention recskit uses everywhere.
    """
    safe_ref = account_ref.replace("'", "''")

    cursor.execute(
        f"""
        SELECT INV_REF, DATE, OUTSTANDING, GROSS_AMOUNT
        FROM AUDIT_HEADER
        WHERE ACCOUNT_REF = '{safe_ref}'
          AND TYPE IN ('PI', 'PC')
          AND DELETED_FLAG = 0
          AND OUTSTANDING <> 0
        ORDER BY DATE
        """
    )
    invoice_rows = cursor.fetchall()

    cursor.execute(
        f"""
        SELECT INV_REF, DATE, GROSS_AMOUNT
        FROM AUDIT_HEADER
        WHERE ACCOUNT_REF = '{safe_ref}'
          AND TYPE = 'PP'
          AND DELETED_FLAG = 0
        ORDER BY DATE DESC
        """
    )
    payment_rows = cursor.fetchall()

    invoices = [
        LedgerInvoice(
            ref=str(r[0]),
            amount=abs(float(r[3] or 0)),
            date=r[1],
            outstanding=float(r[2] or 0),
        )
        for r in invoice_rows
    ]
    payments = [
        LedgerPayment(ref=str(r[0]), amount=abs(float(r[2] or 0)), date=r[1]) for r in payment_rows
    ]

    return invoices, payments
