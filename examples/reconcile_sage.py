"""
reconcile_sage.py -- reconcile a supplier statement against a live
Sage 50 purchase ledger account.

Run with:   python reconcile_sage.py

Requires the "sage" extra (pulls in sagekit):
    pip install recskit[sage]

Before running, set these (or just answer the prompts):
    SAGE_DSN, SAGE_UID, SAGE_PWD -- see sagekit's README

You supply the statement side yourself -- this example hardcodes one
statement's worth of data inline for clarity, but in practice you'd
parse a real PDF/CSV statement into the same StatementItem shapes (see
reconcile_csv.py for a fully worked CSV version).
"""

from datetime import date

from sagekit import connect_or_exit
from recskit import StatementItem, reconcile_statement
from recskit.sage_adapter import find_purchase_ledger_account, pull_purchase_ledger

# --- Fill in with the supplier account you're reconciling ---
SUPPLIER_SEARCH_TERM = "Northwind Beverages"  # matched fuzzily against PURCHASE_LEDGER.NAME
STATEMENT_BALANCE = 1063.45

STATEMENT_ITEMS = [
    StatementItem(type="invoice", ref="INV-100", amount=500.00, date=date(2026, 5, 1)),
    StatementItem(type="invoice", ref="INV-101", amount=320.00, date=date(2026, 5, 10)),
    StatementItem(type="invoice", ref="INV-103", amount=150.00, date=date(2026, 5, 25)),
    StatementItem(type="payment", ref="BACS", amount=300.00, date=date(2026, 5, 15)),
]


def main():
    conn = connect_or_exit()
    try:
        cursor = conn.cursor()

        account_ref, account_name = find_purchase_ledger_account(cursor, SUPPLIER_SEARCH_TERM)
        print(f"Matched Sage account: {account_ref} ({account_name})\n")

        ledger_invoices, ledger_payments = pull_purchase_ledger(cursor, account_ref)

        result = reconcile_statement(
            STATEMENT_ITEMS, ledger_invoices, ledger_payments, statement_balance=STATEMENT_BALANCE
        )

        for r in result.invoice_results + result.payment_results:
            flag = {"ok": "OK", "mismatch": "MISMATCH", "missing": "MISSING"}[r.status]
            print(f"  {r.item.ref:<15} £{r.item.amount:>10,.2f}  {flag:<8} {r.note}")

        print(f"\nStatement balance: £{result.statement_balance:,.2f}")
        print(f"Sage balance:      £{result.ledger_balance:,.2f}")
        print(f"Difference:        £{result.balance_difference:,.2f}")
        print(f"\nRESULT: {'AGREED' if result.agreed else f'{result.issue_count} issue(s) to review'}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
