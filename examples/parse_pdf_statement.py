"""
parse_pdf_statement.py -- turn a statement PDF into StatementItems and
reconcile it against a ledger CSV in one go.

Run with:   python parse_pdf_statement.py statement.pdf ledger.csv "Supplier Name"

Requires the "parse-pdf" extra:
    pip install recskit[parse-pdf]

and an Anthropic API key set as the ANTHROPIC_API_KEY environment
variable (this is the one recskit example that makes a network call --
reconcile_csv.py is the fully offline one).

The third argument (supplier/customer name) is optional but improves
parsing accuracy -- pass any known quirks of their statement format as
a fourth argument, e.g. "prints two references per line for each
invoice; put the second one in alt_ref".

See ledger.csv in this folder for the expected ledger CSV format (the
same one reconcile_csv.py uses) -- this script only replaces the
*statement* side with a real PDF instead of statement.csv.
"""

import sys
from pathlib import Path

from recskit import reconcile_statement
from recskit.pdf_statement import parse_pdf_to_statement

sys.path.insert(0, str(Path(__file__).parent))
from reconcile_csv import load_ledger, print_report  # reuse the CSV ledger loader


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    pdf_path = sys.argv[1]
    ledger_path = sys.argv[2]
    counterparty_name = sys.argv[3] if len(sys.argv) > 3 else ""
    parsing_notes = sys.argv[4] if len(sys.argv) > 4 else ""

    print(f"Extracting and parsing {pdf_path} ...")
    stmt_date, stmt_balance, items = parse_pdf_to_statement(
        pdf_path, counterparty_name=counterparty_name, parsing_notes=parsing_notes
    )
    print(f"Statement date: {stmt_date}, balance: £{stmt_balance:,.2f}, {len(items)} item(s) parsed\n")

    ledger_invoices, ledger_payments = load_ledger(ledger_path)
    result = reconcile_statement(items, ledger_invoices, ledger_payments, statement_balance=stmt_balance)
    print_report(result)


if __name__ == "__main__":
    main()
