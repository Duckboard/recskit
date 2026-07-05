"""
recskit.pdf_statement
======================
Optional module: turns a statement PDF into a list of StatementItem
objects, using pdfplumber to pull out the text and the Claude API to
turn that text into structured data.

This is the part of a real reconciliation workflow that's actually
hard -- matching and arithmetic (the rest of recskit) is comparatively
easy once you have clean structured data. Every supplier or customer
formats their statement differently, and hand-writing a parser per
format doesn't scale. Handing the raw extracted text to an LLM with a
strict output shape does, and adapts to a new statement layout with no
code changes.

Requires the optional "parse-pdf" extra:

    pip install recskit[parse-pdf]

and an Anthropic API key (ANTHROPIC_API_KEY environment variable, or
passed explicitly) -- extract_pdf_text() has no such requirement and
works standalone if you'd rather wire up a different parser.
"""

import json
from datetime import datetime
from typing import List, Optional

from .models import StatementItem

PARSING_SYSTEM_PROMPT = """You are extracting structured data from a supplier or customer \
account statement PDF, for automated reconciliation against an accounting ledger.

Return ONLY valid JSON (no markdown code fences, no commentary) matching exactly this shape:

{
  "statement_date": "DD/MM/YYYY",
  "statement_balance": <number, the total balance due printed at the bottom of the statement>,
  "items": [
    {
      "type": "invoice" | "credit_note" | "payment",
      "ref": "the reference shown on the statement for this line",
      "alt_ref": "a second reference for the same line, if the statement prints two (optional)",
      "amount": <number, always positive regardless of how it is signed on the statement>,
      "date": "DD/MM/YYYY",
      "due_date": "DD/MM/YYYY (optional -- only include if a due date is explicitly printed next to this line)"
    }
  ]
}

Rules:
- Do NOT include a brought-forward / balance-forward line as an item -- it is a summary of
  older transactions, not a document in its own right.
- A payment shown with no document reference (BACS, a bank transfer, etc.) should get a
  short generic "ref" like "bacs" rather than being left blank.
- Credit notes use "type": "credit_note".
- If unsure whether a line is an invoice or credit note, use the sign or column it's shown
  in as a guide.
- Keep dates in whichever format the statement itself uses, consistently, as DD/MM/YYYY
  unless the statement is clearly in another locale's date format.
"""


def extract_pdf_text(pdf_path_or_bytes) -> str:
    """
    Extract all text from a statement PDF, page by page, joined with
    newlines. Accepts a file path (str/Path) or raw PDF bytes.

    This has no dependency on the Claude API -- useful on its own if
    you'd rather feed the text to a different parser (a regex-based
    one for a single known format, another LLM, etc).
    """
    import io

    import pdfplumber

    source = io.BytesIO(pdf_path_or_bytes) if isinstance(pdf_path_or_bytes, bytes) else pdf_path_or_bytes

    parts = []
    with pdfplumber.open(source) as pdf:
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
    return "\n".join(parts)


def parse_statement_text(
    statement_text: str,
    counterparty_name: str = "",
    parsing_notes: str = "",
    api_key: Optional[str] = None,
    model: str = "claude-sonnet-5",
) -> dict:
    """
    Send extracted statement text to the Claude API and get back the
    raw parsed dict (statement_date, statement_balance, items) --
    matching PARSING_SYSTEM_PROMPT's shape exactly.

    `counterparty_name` (the supplier or customer's name) and
    `parsing_notes` (any known quirks of their statement format, e.g.
    "this supplier prints two references per line -- put the second
    one in alt_ref") are optional context that measurably improves
    parsing accuracy for tricky or unusual layouts; both are free text.

    `api_key` falls back to the ANTHROPIC_API_KEY environment variable
    if not passed explicitly -- this function does not read a .env
    file itself.

    Raises whatever the anthropic client raises on an API error, and
    json.JSONDecodeError if the model's response isn't valid JSON
    despite the prompt (rare, but don't assume it's impossible).
    """
    from anthropic import Anthropic

    client = Anthropic(api_key=api_key) if api_key else Anthropic()

    user_prompt = ""
    if counterparty_name:
        user_prompt += f"Statement is from: {counterparty_name}\n"
    if parsing_notes:
        user_prompt += f"Known quirks for this statement format: {parsing_notes}\n"
    user_prompt += f"\nStatement text:\n\n{statement_text}"

    response = client.messages.create(
        model=model,
        max_tokens=4000,
        system=PARSING_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def statement_items_from_parsed(parsed: dict) -> List[StatementItem]:
    """
    Convert the raw dict from parse_statement_text() (or your own
    parser, provided it matches the same shape) into a list of
    StatementItem objects, ready for reconcile_statement().

    Does not touch statement_date / statement_balance -- read those
    directly off `parsed` yourself; reconcile_statement() takes the
    balance as a separate argument rather than as part of this list.
    """
    items = []
    for raw_item in parsed.get("items", []):
        items.append(
            StatementItem(
                type=raw_item["type"],
                ref=raw_item["ref"],
                amount=float(raw_item["amount"]),
                date=_parse_date(raw_item.get("date")),
                alt_ref=raw_item.get("alt_ref", "") or "",
                due_date=_parse_date(raw_item.get("due_date")),
            )
        )
    return items


def parse_pdf_to_statement(
    pdf_path_or_bytes,
    counterparty_name: str = "",
    parsing_notes: str = "",
    api_key: Optional[str] = None,
    model: str = "claude-sonnet-5",
) -> tuple:
    """
    End-to-end convenience: PDF in, (statement_date, statement_balance,
    items) out, ready to hand straight to reconcile_statement().

        from recskit.pdf_statement import parse_pdf_to_statement
        from recskit import reconcile_statement

        stmt_date, stmt_balance, items = parse_pdf_to_statement("statement.pdf", "Acme Supplies")
        result = reconcile_statement(items, ledger_invoices, ledger_payments, stmt_balance)
    """
    text = extract_pdf_text(pdf_path_or_bytes)
    parsed = parse_statement_text(text, counterparty_name, parsing_notes, api_key, model)
    items = statement_items_from_parsed(parsed)
    return _parse_date(parsed.get("statement_date")), float(parsed.get("statement_balance", 0)), items


def _parse_date(value):
    if not value:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None
