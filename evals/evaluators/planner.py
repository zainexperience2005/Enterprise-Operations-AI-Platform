from typing import Any
from app.agents.planner.schemas import InvestigationPlan
from evals.evaluators.schemas import EvalResult


def evaluate_planner_case(
    case: dict[str, Any],
    plan: InvestigationPlan,
    latency_seconds: float = 0.0,
) -> EvalResult:
    """Deterministically evaluates an InvestigationPlan against case expectations.

    Checks:
    1. Are all required specialists present in the plan?
    2. Are all forbidden specialists excluded?
    """
    case_id = case.get("case_id", "PLAN-UNKNOWN")
    required_specialists = set(case.get("required_specialists", []))
    forbidden_specialists = set(case.get("forbidden_specialists", []))

    actual_specialists = {step.specialist for step in plan.steps}

    missing_required = [s for s in required_specialists if s not in actual_specialists]
    present_forbidden = [s for s in forbidden_specialists if s in actual_specialists]

    failures = []
    if missing_required:
        failures.append(f"Missing required specialists: {missing_required}")
    if present_forbidden:
        failures.append(f"Contains forbidden specialists: {present_forbidden}")

    passed = len(failures) == 0

    return EvalResult(
        case_id=case_id,
        passed=passed,
        metrics={
            "required_specialists_satisfied": len(missing_required) == 0,
            "forbidden_specialists_satisfied": len(present_forbidden) == 0,
            "total_steps": len(plan.steps),
            "actual_specialists": ",".join(sorted(actual_specialists)),
        },
        failures=failures,
        latency_seconds=latency_seconds,
        metadata={"category": case.get("category", "general")},
    )
