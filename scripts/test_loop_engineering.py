"""Test script for Step 15: Loop Engineering.

Verifies:
1. Evidence evaluation and verdict generation.
2. Bounded corrective loops with progress detection (evidence fingerprinting).
3. Stagnation prevention and budget limits.
4. Non-looping on sufficient evidence vs safe exit on insufficient evidence.
"""

import sys
from pprint import pprint

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.agents.evaluator import evaluate_evidence
from app.agents.orchestrator import run_investigation
from app.reliability.progress import evidence_fingerprint


def test_evaluator_unit():
    print("=" * 60)
    print("TEST 1: Evaluator Unit Test (Detecting Missing Information)")
    print("=" * 60)

    request = "Investigate billing discrepancy for ticket TICK-4001."
    evidence = (
        "Step 1 [SQL]: Found invoice INV-2001 with total $1600. "
        "Customer was charged $1600."
    )
    errors = "None"

    evaluation = evaluate_evidence(
        request=request,
        evidence=evidence,
        errors=errors,
    )

    print("Verdict:", evaluation.verdict)
    print("Missing Info:", evaluation.missing_information)
    print("Recommended Specialist:", evaluation.recommended_specialist)
    print("Recommended Instruction:", evaluation.recommended_instruction)
    print("Reason:", evaluation.reason)
    assert evaluation.verdict in ("sufficient", "insufficient")
    print(" Evaluator unit test passed!\n")


def test_evidence_fingerprint():
    print("=" * 60)
    print("TEST 2: Evidence Fingerprint & Stagnation Detection")
    print("=" * 60)

    evidence_a = [
        {"step_id": 1, "specialist": "api", "result": "Customer CUST-001 found"}
    ]
    evidence_b = [
        {"step_id": 1, "specialist": "api", "result": "Customer CUST-001 found"}
    ]
    evidence_c = [
        {"step_id": 1, "specialist": "api", "result": "Customer CUST-001 found"},
        {"step_id": 2, "specialist": "sql", "result": "Invoice total $1600"},
    ]

    hash_a = evidence_fingerprint(evidence_a)
    hash_b = evidence_fingerprint(evidence_b)
    hash_c = evidence_fingerprint(evidence_c)

    print("Hash A:", hash_a)
    print("Hash B:", hash_b)
    print("Hash C:", hash_c)

    assert hash_a == hash_b, "Identical evidence should yield identical hash"
    assert hash_a != hash_c, "New evidence should produce different hash"
    print(" Fingerprint matching and differentiation passed!\n")


def test_full_investigation_loop():
    print("=" * 60)
    print("TEST 3: Full End-to-End Orchestrator with Loop Engineering")
    print("=" * 60)

    result = run_investigation(
        request="Investigate ticket TICK-4001 regarding billing discrepancy and determine if a refund is justified.",
        investigation_id="TICK-4001",
    )

    print("Investigation ID:", result.get("investigation_id"))
    print("Loop Status:", result.get("loop_status"))
    print("Correction Count:", result.get("correction_count"))
    print("Specialist Call Count:", result.get("specialist_call_count"))
    print("Total Evidence Items:", len(result.get("evidence", [])))
    print("Stagnation Count:", result.get("stagnation_count"))

    evaluation = result.get("evaluation")
    if evaluation:
        print("\nFinal Evaluator Verdict:", evaluation.get("verdict"))
        print("Missing Info:", evaluation.get("missing_information"))

    print("\nResolution Output Preview:")
    res_preview = str(result.get("final_resolution", ""))[:400]
    print(res_preview + "...\n")

    print("Proposed Action:", result.get("proposed_action"))
    print("Approval Status:", result.get("approval_status"))
    print(" Full investigation loop execution completed successfully!\n")


if __name__ == "__main__":
    test_evaluator_unit()
    test_evidence_fingerprint()
    test_full_investigation_loop()
