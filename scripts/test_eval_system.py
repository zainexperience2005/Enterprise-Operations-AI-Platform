"""Quick test script to verify all Step 16 evaluators."""

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from evals.evaluators.action_safety import evaluate_action_safety_case
from evals.evaluators.groundedness import evaluate_groundedness
from evals.evaluators.planner import evaluate_planner_case
from evals.evaluators.sql import evaluate_sql_case
from app.agents.planner.schemas import InvestigationPlan, PlanStep


def test_sql_evaluator():
    print("=" * 60)
    print("TEST: SQL Evaluation Suite")
    print("=" * 60)
    path = Path("evals/datasets/sql_cases.json")
    with open(path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    passed_count = 0
    for case in cases:
        result = evaluate_sql_case(case)
        if result.passed:
            passed_count += 1
            print(f" PASS: {case['case_id']} - {case['description']}")
        else:
            print(f" FAIL: {case['case_id']} - {result.failures}")

    print(f"Result: {passed_count}/{len(cases)} passed\n")
    assert passed_count == len(cases), "All SQL cases should pass!"


def test_safety_evaluator():
    print("=" * 60)
    print("TEST: Action Safety Evaluation Suite")
    print("=" * 60)
    path = Path("evals/datasets/safety_cases.json")
    with open(path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    passed_count = 0
    for case in cases:
        result = evaluate_action_safety_case(case)
        if result.passed:
            passed_count += 1
            print(f" PASS: {case['case_id']} - {case['description']}")
        else:
            print(f" FAIL: {case['case_id']} - {result.failures}")

    print(f"Result: {passed_count}/{len(cases)} passed\n")
    assert passed_count == len(cases), "All safety cases should pass!"


def test_groundedness_judge():
    print("=" * 60)
    print("TEST: Groundedness LLM-as-a-Judge")
    print("=" * 60)

    evidence = "Invoice INV-2001 total is $1600. Order ORD-1001 approved total was $1400."

    # Grounded case
    res_grounded = evaluate_groundedness(
        case_id="GND-001",
        evidence=evidence,
        answer="The invoice total of $1600 exceeds the approved order total of $1400 by $200.",
    )
    print(f"Grounded test: {'PASS' if res_grounded.passed else 'FAIL'} - reason: {res_grounded.metadata.get('reason')}")
    assert res_grounded.passed, "Accurate answer should be evaluated as grounded"

    # Ungrounded case (hallucinated facts)
    res_ungrounded = evaluate_groundedness(
        case_id="GND-002",
        evidence=evidence,
        answer="Customer VIP-99 was overcharged by $500 on their annual software subscription.",
    )
    print(f"Ungrounded test: {'PASS' if not res_ungrounded.passed else 'FAIL'} - unsupported claims: {res_ungrounded.failures}")
    assert not res_ungrounded.passed, "Hallucinated claim should be marked ungrounded"
    print(" Groundedness judge unit test passed!\n")


if __name__ == "__main__":
    test_sql_evaluator()
    test_safety_evaluator()
    test_groundedness_judge()
    print(" All Evaluator Unit Tests Passed Successfully!")
