from typing import Any
from app.db.sql.validator import UnsafeSQLQueryError, validate_sql
from evals.evaluators.schemas import EvalResult


def evaluate_sql_case(
    case: dict[str, Any],
) -> EvalResult:
    """Evaluates SQL query validation safety and correctness.

    Verifies:
    1. Valid queries pass safe SELECT AST parsing.
    2. Malicious/DML/DDL queries are strictly rejected with UnsafeSQLQueryError.
    """
    case_id = case.get("case_id", "SQL-UNKNOWN")
    query = case.get("query", "")
    should_pass = case.get("should_pass_validation", True)

    failures = []
    validation_passed = False
    error_message = None

    try:
        validated = validate_sql(query)
        validation_passed = True
    except UnsafeSQLQueryError as exc:
        validation_passed = False
        error_message = str(exc)
    except Exception as exc:
        validation_passed = False
        error_message = f"Unexpected error: {str(exc)}"

    if should_pass and not validation_passed:
        failures.append(f"Safe query was rejected: {error_message}")
    elif not should_pass and validation_passed:
        failures.append("Malicious/forbidden query passed validation unexpectedly!")

    passed = len(failures) == 0

    return EvalResult(
        case_id=case_id,
        passed=passed,
        metrics={
            "should_pass_validation": should_pass,
            "validation_passed": validation_passed,
            "security_check_passed": passed,
        },
        failures=failures,
        metadata={
            "category": case.get("category", "general"),
            "description": case.get("description", ""),
        },
    )
