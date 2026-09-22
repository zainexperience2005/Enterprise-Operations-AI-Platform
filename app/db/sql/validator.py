from dataclasses import dataclass

import sqlglot
from sqlglot import exp


class UnsafeSQLQueryError(Exception):
    """Raised when SQL violates our safe-query policy."""


@dataclass
class ValidatedQuery:
    sql: str


FORBIDDEN_EXPRESSIONS = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Alter,
    exp.Create,
    exp.TruncateTable,
    exp.Command,
)


def validate_sql(
    query: str,
    max_rows: int = 100,
) -> ValidatedQuery:

    try:
        statements = sqlglot.parse(
            query,
            read="postgres",
        )
    except sqlglot.errors.ParseError as exc:
        raise UnsafeSQLQueryError(
            "Invalid SQL syntax."
        ) from exc

    if len(statements) != 1:
        raise UnsafeSQLQueryError(
            "Only one SQL statement is allowed."
        )

    statement = statements[0]

    if not isinstance(statement, exp.Select):
        raise UnsafeSQLQueryError(
            "Only SELECT queries are allowed."
        )

    for forbidden_type in FORBIDDEN_EXPRESSIONS:
        if statement.find(forbidden_type):
            raise UnsafeSQLQueryError(
                "Query contains a forbidden SQL operation."
            )

    limit = statement.args.get("limit")

    if limit is None:
        statement = statement.limit(max_rows)

    else:
        limit_expression = limit.expression

        try:
            requested_limit = int(
                limit_expression.name
            )
        except (TypeError, ValueError):
            raise UnsafeSQLQueryError(
                "LIMIT must be a fixed integer."
            )

        if requested_limit > max_rows:
            statement.set(
                "limit",
                exp.Limit(
                    expression=exp.Literal.number(
                        max_rows
                    )
                ),
            )

    return ValidatedQuery(
        sql=statement.sql(dialect="postgres")
    )
