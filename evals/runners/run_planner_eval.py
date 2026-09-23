import json
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.agents.planner.planner import create_investigation_plan
from evals.evaluators.planner import evaluate_planner_case

DATASET_PATH = Path(__file__).resolve().parent.parent / "datasets" / "planner_cases.json"


def run_planner_eval():
    print("=" * 65)
    print("RUNNING PLANNER EVALUATION SUITE")
    print("=" * 65)

    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        cases = json.load(f)

    results = []
    total_start = time.time()

    for idx, case in enumerate(cases, 1):
        case_id = case["case_id"]
        inp = case["input"]
        print(f"[{idx}/{len(cases)}] Evaluating {case_id}...")

        start = time.time()
        try:
            plan = create_investigation_plan(user_request=inp)
            duration = time.time() - start
            result = evaluate_planner_case(case, plan, latency_seconds=duration)
        except Exception as exc:
            duration = time.time() - start
            from evals.evaluators.schemas import EvalResult
            result = EvalResult(
                case_id=case_id,
                passed=False,
                failures=[f"Planner crashed: {str(exc)}"],
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
    print("PLANNER EVALUATION SUMMARY")
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
    run_planner_eval()
