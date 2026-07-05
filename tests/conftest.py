"""
pytest fixtures shared across the recskit test suite.

recskit's core logic (models, due_dates, matching, reconcile) has no
external dependencies at all, so most tests need nothing special. Only
test_sage_adapter.py touches anything Sage-shaped, and it uses a fake
cursor rather than a real pyodbc/sagekit connection -- see FakeCursor
below.
"""


class FakeCursor:
    """
    A minimal stand-in for a pyodbc cursor, good enough to exercise
    recskit.sage_adapter without a real Sage connection.

    `query_results` maps a substring that will appear in the SQL (e.g.
    "PURCHASE_LEDGER" or "TYPE = 'PP'") to the rows fetchall() should
    return for that query. Queries are matched in the order given, so
    put more specific substrings first if a query could match more
    than one entry.
    """

    def __init__(self, query_results):
        self._query_results = query_results
        self.last_sql = None
        self._last_rows = []

    def execute(self, sql, *params):
        self.last_sql = sql
        upper = sql.upper()
        for key, rows in self._query_results:
            if key in upper:
                self._last_rows = rows
                return
        raise AssertionError(f"No fake result registered for query: {sql}")

    def fetchall(self):
        return self._last_rows

    def fetchone(self):
        return self._last_rows[0] if self._last_rows else None
