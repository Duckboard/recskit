"""
recskit -- reconcile a supplier or customer statement against your own
accounting ledger: match invoices, credit notes, and payments, flag
mismatches and missing items, and compare balances.

The core logic has no dependencies at all and doesn't care where your
data came from -- CSV, a PDF you parsed by hand, Sage, Xero,
QuickBooks. recskit.sage_adapter is one optional, concrete way to pull
the ledger side out of Sage 50 (via sagekit); write your own equivalent
for anything else.

    from recskit import StatementItem, LedgerInvoice, LedgerPayment
    from recskit import reconcile_statement, calc_due_date

See README.md for the full walkthrough.
"""

from .due_dates import DUE_FROM_MODES, calc_due_date
from .matching import find_best_name_match, match_invoice, match_payment, normalize_name
from .models import (
    LedgerInvoice,
    LedgerPayment,
    MatchResult,
    ReconciliationResult,
    StatementItem,
)
from .reconcile import reconcile_statement

__version__ = "0.1.0"

__all__ = [
    "StatementItem",
    "LedgerInvoice",
    "LedgerPayment",
    "MatchResult",
    "ReconciliationResult",
    "reconcile_statement",
    "match_invoice",
    "match_payment",
    "normalize_name",
    "find_best_name_match",
    "calc_due_date",
    "DUE_FROM_MODES",
    "__version__",
]
