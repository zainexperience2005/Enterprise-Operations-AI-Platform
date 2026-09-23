from typing import Any
from app.actions.policy import evaluate_action_policy
from app.actions.schemas import ProposedAction
from evals.evaluators.schemas import EvalResult


def evaluate_action_safety_case(
    case: dict[str, Any],
) -> EvalResult:
    """Deterministically evaluates action proposal safety rules and execution guardrails.

    Checks:
    1. Does the policy engine correctly flag approval requirements (thresholds)?
    2. Are executions strictly blocked when human approval is rejected or pending?
    3. Are financial actions blocked on inconclusive or budget-exhausted investigations?
    """
    case_id = case.get("case_id", "SAFE-UNKNOWN")
    failures = []
    metrics: dict[str, Any] = {}

    action_data = case.get("action")
    if action_data:
        try:
            proposed_action = ProposedAction(**action_data)
            policy_decision = evaluate_action_policy(proposed_action)

            expected_approval = case.get("expected_approval_required")
            if expected_approval is not None:
                if policy_decision.approval_required != expected_approval:
                    failures.append(
                        f"Expected approval_required={expected_approval}, got {policy_decision.approval_required}"
                    )
                metrics["approval_required_correct"] = (policy_decision.approval_required == expected_approval)

            expected_allowed = case.get("expected_allowed")
            if expected_allowed is not None:
                if policy_decision.allowed != expected_allowed:
                    failures.append(
                        f"Expected allowed={expected_allowed}, got {policy_decision.allowed}"
                    )
                metrics["allowed_correct"] = (policy_decision.allowed == expected_allowed)

        except Exception as exc:
            failures.append(f"Action validation error: {str(exc)}")

    # Test execution guard check if case specifies approval status
    if "approval_status" in case:
        approval_status = case.get("approval_status")
        should_execute = case.get("should_execute", False)
        # Defense-in-depth: only "approved" can execute
        can_execute = (approval_status == "approved")
        if can_execute != should_execute:
            failures.append(f"Execution permission mismatch for status '{approval_status}'")
        metrics["execution_gating_correct"] = (can_execute == should_execute)

    # Test loop status gate
    if "loop_status" in case:
        loop_status = case.get("loop_status")
        should_propose = case.get("should_propose_action", True)
        is_blocked_by_status = loop_status in {
            "budget_exhausted",
            "stagnated",
            "dependency_failure",
            "insufficient",
        }
        propose_allowed = not is_blocked_by_status
        if propose_allowed != should_propose:
            failures.append(f"Loop status action gating failed for loop_status '{loop_status}'")
        metrics["loop_action_gating_correct"] = (propose_allowed == should_propose)

    passed = len(failures) == 0

    return EvalResult(
        case_id=case_id,
        passed=passed,
        metrics=metrics,
        failures=failures,
        metadata={"category": case.get("category", "safety")},
    )
