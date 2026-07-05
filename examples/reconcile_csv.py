"""
reconcile_csv.py -- reconcile a statement against a ledger, both read
from plain CSV files. No Sage, no database, no network -- good for a
quick check, or as a template for wiring recskit up to whatever export
your own accounting system produces.

Run with:   python reconcile_csv.py statement.csv ledger.csv <balance>

statement.csv columns: type,ref,alt_ref,amount,date,due_date
    type       -- invoice | credit_note | payment
    ref        -- the reference shown on the statement
    alt_ref    -- optional second reference for the same line
    amount     -- always positive
    date       -- DD/MM/YYYY
    due_date   -- DD/MM/YYYY, optional (leave blank to skip)

ledger.csv columns: type,ref,amount,date,outstanding
    type        -- invoice | credit_note | payment
    ref         -- the reference in your ledger
    amount      -- gross amount, positive
    date        -- DD/MM/YYYY
    outstanding -- for invoices/credit notes only; ignored for payments

Sample files (statement.csv / ledger.csv) are included alongside this
script -- run the command above with no arguments to try them.
"""

import csv
import sys
from datetime import datetime
from pathlib import Path

from recskit import LedgerInvoice, LedgerPayment, StatementItem, reconcile_statement

SCRIPT_DIR = Path(__file__).parent


def parse_date(s):
    s = (s or "").strip()
    return datetime.strptime(s, "%d/%m/%Y").date() if s else None


def load_statement_items(path):
    items = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            items.append(
                StatementItem(
                    type=row["type"].strip(),
                    ref=row["ref"].strip(),
                    alt_ref=(row.get("alt_ref") or "").strip(),
                    amount=float(row["amount"]),
                    date=parse_date(row.get("date")),
                    due_date=parse_date(row.get("due_date")),
                )
            )
    return items


def load_ledger(path):
    invoices, payments = [], []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["type"].strip() == "payment":
                payments.append(
                    LedgerPayment(ref=row["ref"].strip(), amount=float(row["amount"]), date=parse_date(row.get("date")))
                )
            else:
                invoices.append(
                    LedgerInvoice(
                        ref=row["ref"].strip(),
                        amount=float(row["amount"]),
                        date=parse_date(row.get("date")),
                        outstanding=float(row.get("outstanding") or 0),
                    )
                )
    return invoices, payments


def print_report(result):
    print("INVOICES / CREDIT NOTES")
    for r in result.invoice_results:
        flag = {"ok": "OK", "mismatch": "MISMATCH", "missing": "MISSING"}[r.status]
        print(f"  {r.item.ref:<15} stmt £{r.item.amount:>10,.2f}  {flag:<8} {r.note}")

    if result.payment_results:
        print("\nPAYMENTS")
        for r in result.payment_results:
            flag = {"ok": "OK", "mismatch": "MISMATCH", "missing": "MISSING"}[r.status]
            print(f"  {r.item.ref:<15} stmt £{r.item.amount:>10,.2f}  {flag:<8} {r.note}")

    if result.extra_in_ledger:
        print("\nIN LEDGER, NOT ON STATEMENT (check brought-forward balance):")
        for inv in result.extra_in_ledger:
            print(f"  {inv.ref:<15} £{inv.amount:>10,.2f}  outstanding £{inv.outstanding:>10,.2f}")

    print(f"\nStatement balance: £{result.statement_balance:,.2f}")
    print(f"Ledger balance:    £{result.ledger_balance:,.2f}")
    print(f"Difference:        £{result.balance_difference:,.2f}")
    print(f"\nRESULT: {'AGREED' if result.agreed else f'{result.issue_count} issue(s) to review'}")


def main():
    args = sys.argv[1:]
    if len(args) == 3:
        stmt_path, ledger_path, balance = args
    elif not args:
        stmt_path = SCRIPT_DIR / "statement.csv"
        ledger_path = SCRIPT_DIR / "ledger.csv"
        balance = "1063.45"  # matches the sample files
        print(f"No arguments given -- using the sample files in {SCRIPT_DIR}\n")
    else:
        print(__doc__)
        sys.exit(1)

    items = load_statement_items(stmt_path)
    ledger_invoices, ledger_payments = load_ledger(ledger_path)

    result = reconcile_statement(
        items, ledger_invoices, ledger_payments, statement_balance=float(balance)
    )
    print_report(result)


if __name__ == "__main__":
    main()
