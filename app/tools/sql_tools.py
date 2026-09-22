from langchain_core.tools import tool

from app.db.sql.executor import execute_safe_query
from app.db.sql.schema import get_database_schema
from app.db.sql.validator import UnsafeSQLQueryError
from app.tools.schemas import SQLQueryInput


@tool
def inspect_database_schema() -> dict:
    """
    Return the allowed enterprise database schema.

    Use this before writing SQL when table or column
    structure is uncertain.
    """

    return get_database_schema()


@tool(args_schema=SQLQueryInput)
def execute_sql_query(query: str) -> dict:
    """
    Execute one safe, read-only PostgreSQL SELECT query.

    The query is validated and automatically limited.
    Destructive or mutation queries are prohibited.
    """

    try:
        return execute_safe_query(query)

    except UnsafeSQLQueryError as exc:
        return {
            "success": False,
            "error": str(exc),
        }

    except Exception:
        return {
            "success": False,
            "error": "SQL query execution failed.",
        }


SQL_TOOLS = [
    inspect_database_schema,
    execute_sql_query,
]