# recskit

Reconcile a supplier or customer statement against your own accounting
ledger: match invoices, credit notes, and payments; flag mismatches
and missing items on either side; compare balances. The core has
**zero dependencies** and doesn't care where your data came from --
CSV, a PDF you parsed by hand, Sage, Xero, QuickBooks, anything.

If this saves you time, consider [buying me a coffee](https://ko-fi.com/fredscripts).

## What problem this solves

Checking a supplier statement against your own ledger by eye is slow
and error-prone, especially once an account has more than a handful of
open items. Two things make it worse than it looks:

1. **A tied-up total balance doesn't mean every line is right.** Two
   errors can cancel out -- a mismatched invoice and a missing one can
   add up to the same total as if nothing were wrong. recskit checks
   every line, not just the bottom-line figure.
2. **Reference matching is a trap.** A short reference like `991` can
   turn up as a *substring* of an unrelated, older invoice's reference
   (`INV-99910`) on a long-standing account. Match on substring first
   and you'll silently pair the statement line with the wrong invoice,
   reporting a confident-looking "mismatch" instead of correctly
   reporting no match at all. recskit always tries an **exact**
   reference match before ever falling back to substring matching.

## Features

- Matches invoices/credit notes by reference (with support for
  statements that print two references for the same line), payments
  by amount first then reference
- Exact-match-first, substring-fallback matching order -- see above
- Configurable payment-terms due-date calculation (flat N days,
  N days from the start of the following month, N days from end of
  month, or end of the following month with no offset)
- Flags items in your ledger that never show up on the statement at
  all (commonly an old item sitting in a brought-forward balance)
- Zero required dependencies in the core -- add the optional `sage`
  extra only if you want the bundled Sage 50 adapter
- Two worked examples: pure CSV (no external system at all), and Sage
  50 via [sagekit](https://github.com/FredScriptsPT/sagekit)

## Installation

```bash
pip install -r requirements.txt      # core only, zero dependencies
pip install -e .                     # or, as an editable package
pip install -e ".[sage]"             # + the optional Sage 50 adapter
```

## Usage

```python
from recskit import StatementItem, LedgerInvoice, LedgerPayment, reconcile_statement

items = [
    StatementItem(type="invoice", ref="INV-100", amount=500.00),
    StatementItem(type="invoice", ref="INV-101", amount=320.00),
    StatementItem(type="payment", ref="bacs", amount=300.00),
]

ledger_invoices = [
    LedgerInvoice(ref="INV-100", amount=500.00, outstanding=500.00),
    LedgerInvoice(ref="INV-101", amount=300.00, outstanding=300.00),
]
ledger_payments = [LedgerPayment(ref="BACS-9001", amount=300.00)]

result = reconcile_statement(items, ledger_invoices, ledger_payments, statement_balance=800.00)

print(result.agreed, result.issue_count, result.balance_difference)
for r in result.mismatched_items + result.missing_items:
    print(r.item.ref, r.status, r.note)
```

### Payment-terms due dates

```python
from datetime import date
from recskit import calc_due_date

calc_due_date(date(2026, 5, 14), 30)                                   # 30 days from invoice date
calc_due_date(date(2026, 5, 14), 29, "start_of_following_month")       # 29 days from 1 June
calc_due_date(date(2026, 5, 3), 14, "end_of_month")                    # 14 days from 31 May
calc_due_date(date(2026, 5, 3), 0, "end_of_following_month")           # 30 June, terms_days ignored
```

### Examples

```bash
python examples/reconcile_csv.py                         # runs on the bundled sample CSVs
python examples/reconcile_csv.py statement.csv ledger.csv 1063.45   # your own files
python examples/reconcile_sage.py                         # requires the "sage" extra + a live Sage 50
```

`reconcile_csv.py` needs no external system at all -- a good starting
point for wiring recskit up to whatever export your own accounting
software produces. `reconcile_sage.py` shows the same reconciliation
against a live Sage 50 purchase ledger account, using
`recskit.sage_adapter` to fetch the ledger side and
[sagekit](https://github.com/FredScriptsPT/sagekit) for the ODBC
connection and column auto-detection.

### Concept reference

| Concept | Meaning |
|---|---|
| `StatementItem` | One line from the statement you're checking (invoice, credit note, or payment) |
| `LedgerInvoice` / `LedgerPayment` | The equivalent transaction as it exists in your own ledger |
| `MatchResult.status` | `"ok"`, `"mismatch"` (found but wrong amount), or `"missing"` (no match at all) |
| `extra_in_ledger` | Ledger invoices never referenced by any statement line -- check these aren't being missed, or are simply old brought-forward items |
| `balance_difference` | `ledger_balance - statement_balance` |

## Bring your own data source

The reconciliation logic never touches a database, file, or network --
you build `StatementItem` / `LedgerInvoice` / `LedgerPayment` lists
however suits your setup, and call `reconcile_statement()`. Options:

- Parse a PDF or CSV statement export yourself (see
  `examples/reconcile_csv.py`)
- Pull the ledger side from Sage 50 with `recskit.sage_adapter` (see
  `examples/reconcile_sage.py`)
- Write your own adapter for Xero, QuickBooks, or anything else --
  `sage_adapter.py` is about 100 lines and a reasonable template to
  copy

## Testing

```bash
pip install pytest
pytest
```

The core test suite has no dependencies to mock -- it's all plain
Python objects in, plain Python objects out.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| A statement line matches the wrong ledger invoice | Shouldn't happen -- recskit always tries an exact ref match before substring | If you see this, please open an issue with the two refs involved |
| Balance agrees but you still see mismatches/missing items | This is expected and correct -- see "What problem this solves" above | Investigate each flagged line; a tied total doesn't guarantee every line is right |
| Payment shows as missing despite being in the ledger | Amount differs by more than the tolerance, and the reference also doesn't appear as a substring | Widen `tolerance` in `match_payment()`, or check the payment was recorded correctly |
| `ImportError` on `sagekit` | The `sage` extra wasn't installed | `pip install -e ".[sage]"`, or install sagekit directly |

## License

MIT -- see [LICENSE](LICENSE). Do whatever you like with this; a
credit or a [Ko-fi tip](https://ko-fi.com/fredscripts) is appreciated
but never required.
