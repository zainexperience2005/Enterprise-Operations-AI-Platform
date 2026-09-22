import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pprint import pprint

from app.db.sql.executor import execute_safe_query


result = execute_safe_query(
    """
    SELECT
        invoice_number,
        amount,
        status
    FROM invoices
    """
)

pprint(result)