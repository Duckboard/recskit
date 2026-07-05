"""
recskit.matching
=================
Matches individual statement lines against ledger transactions.

The core lesson baked into this module: **always try an exact
reference match before falling back to a substring match.** A short
reference like "9910" can accidentally turn up as a *substring* of an
unrelated, older invoice's reference on a long-standing account. If you
match on substring first, you silently pair the statement line with
the wrong ledger invoice -- and report a confident-looking "mismatch"
amount instead of correctly reporting no match at all. This bit a real
reconciliation run before the exact-match-first rule was added, so
it's not a hypothetical -- keep the ordering.
"""

import re
from typing import List, Optional, Tuple

from .models import LedgerInvoice, LedgerPayment, MatchResult, StatementItem


def normalize_name(name: str) -> str:
    """
    Strip everything except letters and digits and uppercase the rest.
    Account/company names are rarely entered consistently ("N.D. John"
    vs "ND John", "St." vs "St", extra spaces) -- comparing on
    letters/digits only avoids false negatives from punctuation alone.
    """
    return re.sub(r"[^A-Z0-9]", "", (name or "").upper())


def find_best_name_match(
    search_term: str, candidates: List[Tuple[str, str]], tie_breaker_counts: Optional[dict] = None
) -> Optional[Tuple[str, str]]:
    """
    Find the best match for `search_term` among `candidates`, a list of
    (id, name) tuples, using normalize_name() for a punctuation-
    insensitive comparison.

    Returns the matching (id, name) tuple, or None if nothing matches.
    If more than one candidate matches, `tie_breaker_counts` (a dict of
    id -> some comparable score, e.g. transaction count) picks the
    highest-scoring one; without it, the first match wins.
    """
    norm_search = normalize_name(search_term)
    matches = [c for c in candidates if norm_search in normalize_name(c[1])]

    if not matches:
        return None
    if len(matches) == 1 or not tie_breaker_counts:
        return matches[0]

    return max(matches, key=lambda c: tie_breaker_counts.get(c[0], 0))


def match_invoice(
    item: StatementItem, ledger_invoices: List[LedgerInvoice], tolerance: float = 0.01
) -> MatchResult:
    """
    Match one invoice/credit-note statement line against the ledger.

    Tries an exact match on `ref` (and `alt_ref`, if the statement
    supplied a second reference for this line) first. Only if nothing
    matches exactly does it fall back to a substring match -- see the
    module docstring for why the ordering matters.
    """
    refs_to_try = [item.ref.upper()]
    if item.alt_ref:
        refs_to_try.append(item.alt_ref.upper())

    exact = [inv for inv in ledger_invoices if inv.ref.upper() in refs_to_try]
    candidates = exact or [
        inv for inv in ledger_invoices if any(r in inv.ref.upper() for r in refs_to_try)
    ]

    if not candidates:
        return MatchResult(item=item, status="missing", note=f"No ledger entry for ref {item.ref!r}")

    ledger_invoice = candidates[0]
    if abs(ledger_invoice.amount - item.amount) < tolerance:
        return MatchResult(
            item=item, status="ok", ledger_ref=ledger_invoice.ref, ledger_amount=ledger_invoice.amount
        )

    return MatchResult(
        item=item,
        status="mismatch",
        ledger_ref=ledger_invoice.ref,
        ledger_amount=ledger_invoice.amount,
        note=f"Statement £{item.amount:,.2f} vs ledger £{ledger_invoice.amount:,.2f}",
    )


def match_payment(
    item: StatementItem, ledger_payments: List[LedgerPayment], tolerance: float = 0.01
) -> MatchResult:
    """
    Match one payment statement line against the ledger.

    Payments are matched by **amount first**, then by reference text --
    the opposite order to invoices. This is deliberate: payment
    references (BACS refs, bank descriptions) very often differ
    between what a supplier's statement shows and what actually lands
    in your ledger, whereas the amount is reliable.
    """
    by_amount = [p for p in ledger_payments if abs(p.amount - item.amount) < tolerance]
    candidates = by_amount or [
        p for p in ledger_payments if item.ref and item.ref.upper() in (p.ref or "").upper()
    ]

    if not candidates:
        return MatchResult(item=item, status="missing", note=f"No ledger payment matching £{item.amount:,.2f}")

    payment = candidates[0]
    return MatchResult(item=item, status="ok", ledger_ref=payment.ref, ledger_amount=payment.amount)
