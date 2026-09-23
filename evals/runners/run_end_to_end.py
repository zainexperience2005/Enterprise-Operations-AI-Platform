import json
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.agents.orchestrator import run_investigation
from evals.evaluators.task_success import evaluate_task_success
from evals.evaluators.schemas import EvalResult

DATASET_PATH = Path(__file__).resolve().parent.parent / "datasets" / "investigation_cases.json"


def run_end_to_end_eval():
    print("=" * 65)
    print("RUNNING END-TO-END INVESTIGATION EVALUATION SUITE")
    print("=" * 65)

    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        cases = json.load(f)

    results = []
    total_start = time.time()

    for idx, case in enumerate(cases, 1):
        case_id = case["case_id"]
        req = case["request"]
        inv_id = case.get("investigation_id")
        print(f"[{idx}/{len(cases)}] Executing investigation {case_id} ('{inv_id}')...")

        start = time.time()
        try:
            final_state = run_investigation(
                request=req,
                investigation_id=inv_id,
            )
            duration = time.time() - start
            result = evaluate_task_success(
                case=case,
                final_state=final_state,
                latency_seconds=duration,
            )
        except Exception as exc:
            duration = time.time() - start
            result = EvalResult(
                case_id=case_id,
                passed=False,
                failures=[f"Workflow execution crashed: {str(exc)}"],
                latency_seconds=duration,
            )

        results.append(result)
        status_icon = " PASS" if result.passed else " FAIL"
        print(f"       -> {status_icon} ({duration:.2f}s) - {result.failures or 'OK'}")

    total_duration = time.time() - total_start
    passed_count = sum(1 for r in results if r.passed)
    pass_rate = (passed_count / len(results)) * 100 if results else 0
    avg_latency = sum(r.latency_seconds for r in results) / len(results) if results else 0

    print("\n" + "=" * 65)
    print("END-TO-END EVALUATION SUMMARY")
    print("=" * 65)
    print(f"Total Cases:     {len(results)}")
    print(f"Passed:          {passed_count}")
    print(f"Failed:          {len(results) - passed_count}")
    print(f"Pass Rate:       {pass_rate:.1f}%")
    print(f"Avg Latency:     {avg_latency:.2f}s")
    print(f"Total Runtime:   {total_duration:.2f}s")
    print("=" * 65 + "\n")

    return results


if __name__ == "__main__":
    run_end_to_end_eval()
