"""
recskit.models
==============
Plain data containers used throughout recskit. Nothing in this module
talks to any external system -- these are just the shapes that
statement lines and ledger transactions get put into before matching.
"""

from dataclasses import dataclass, field
from datetime import date as date_type
from typing import List, Optional

VALID_ITEM_TYPES = ("invoice", "credit_note", "payment")


@dataclass
class StatementItem:
    """
    One line from a supplier or customer statement.

    `amount` is always positive, regardless of how the statement itself
    signs it (some show purchases as negative, some don't -- normalise
    to positive before creating this).

    `alt_ref` covers statements that print two references for the same
    line (e.g. an internal "Reference" plus their own "Invoice No.") --
    your ledger might have it booked under either one.
    """

    type: str
    ref: str
    amount: float
    date: Optional[date_type] = None
    alt_ref: str = ""
    due_date: Optional[date_type] = None

    def __post_init__(self):
        if self.type not in VALID_ITEM_TYPES:
            raise ValueError(
                f"StatementItem.type must be one of {VALID_ITEM_TYPES}, got {self.type!r}"
            )


@dataclass
class LedgerInvoice:
    """An invoice or credit note as it exists in your accounting ledger."""

    ref: str
    amount: float  # gross amount, positive
    date: Optional[date_type] = None
    outstanding: float = 0.0


@dataclass
class LedgerPayment:
    """A payment as it exists in your accounting ledger."""

    ref: str
    amount: float  # positive
    date: Optional[date_type] = None


@dataclass
class MatchResult:
    """The outcome of trying to match one statement item against the ledger."""

    item: StatementItem
    status: str  # "ok", "mismatch", or "missing"
    ledger_ref: Optional[str] = None
    ledger_amount: Optional[float] = None
    note: str = ""


@dataclass
class ReconciliationResult:
    """
    Everything you need to report on a single statement's reconciliation
    against your ledger.
    """

    invoice_results: List[MatchResult] = field(default_factory=list)
    payment_results: List[MatchResult] = field(default_factory=list)
    extra_in_ledger: List[LedgerInvoice] = field(default_factory=list)
    statement_balance: float = 0.0
    ledger_balance: float = 0.0
    balance_difference: float = 0.0
    issue_count: int = 0
    agreed: bool = True

    @property
    def missing_items(self) -> List[MatchResult]:
        return [r for r in self.invoice_results + self.payment_results if r.status == "missing"]

    @property
    def mismatched_items(self) -> List[MatchResult]:
        return [r for r in self.invoice_results + self.payment_results if r.status == "mismatch"]
