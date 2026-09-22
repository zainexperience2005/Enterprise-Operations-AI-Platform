from typing import Any

from sqlalchemy import text

from app.db.session import readonly_engine
from app.db.sql.validator import validate_sql


DEFAULT_TIMEOUT_MS = 5000
DEFAULT_MAX_ROWS = 100


def execute_safe_query(
    query: str,
    max_rows: int = DEFAULT_MAX_ROWS,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
) -> dict[str, Any]:

    validated = validate_sql(
        query=query,
        max_rows=max_rows,
    )

    with readonly_engine.begin() as connection:

        connection.execute(
            text(
                f"SET LOCAL statement_timeout = {timeout_ms}"
            )
        )

        result = connection.execute(
            text(validated.sql)
        )

        rows = [
            dict(row._mapping)
            for row in result.fetchall()
        ]

    return {
        "sql": validated.sql,
        "row_count": len(rows),
        "rows": rows,
    }