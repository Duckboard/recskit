"""
Tests for the pure-logic parts of recskit.pdf_statement -- converting
an already-parsed dict into StatementItem objects. extract_pdf_text()
and parse_statement_text() need pdfplumber/anthropic and a real PDF or
API call respectively, so they're exercised by hand via
examples/parse_pdf_statement.py rather than in the automated suite.
"""

from datetime import date

from recskit.pdf_statement import statement_items_from_parsed


def test_statement_items_from_parsed_basic():
    parsed = {
        "statement_date": "03/06/2026",
        "statement_balance": 1063.45,
        "items": [
            {"type": "invoice", "ref": "INV-100", "amount": 500.00, "date": "01/05/2026"},
            {"type": "payment", "ref": "bacs", "amount": 300.00, "date": "15/05/2026"},
        ],
    }

    items = statement_items_from_parsed(parsed)

    assert len(items) == 2
    assert items[0].type == "invoice"
    assert items[0].ref == "INV-100"
    assert items[0].amount == 500.00
    assert items[0].date == date(2026, 5, 1)
    assert items[1].type == "payment"


def test_statement_items_from_parsed_with_alt_ref_and_due_date():
    parsed = {
        "items": [
            {
                "type": "invoice",
                "ref": "FBEH2328",
                "alt_ref": "FBIH4586",
                "amount": 371.64,
                "date": "10/04/2026",
                "due_date": "23/05/2026",
            }
        ]
    }

    items = statement_items_from_parsed(parsed)

    assert items[0].alt_ref == "FBIH4586"
    assert items[0].due_date == date(2026, 5, 23)


def test_statement_items_from_parsed_missing_optional_fields():
    parsed = {"items": [{"type": "credit_note", "ref": "CN-1", "amount": 50.0, "date": "01/01/2026"}]}

    items = statement_items_from_parsed(parsed)

    assert items[0].alt_ref == ""
    assert items[0].due_date is None


def test_statement_items_from_parsed_empty_items():
    assert statement_items_from_parsed({"items": []}) == []
    assert statement_items_from_parsed({}) == []
