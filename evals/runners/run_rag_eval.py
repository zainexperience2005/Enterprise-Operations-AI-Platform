import json
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.rag.crag.graph import run_crag
from evals.evaluators.rag import evaluate_rag_retrieval
from evals.evaluators.schemas import EvalResult

DATASET_PATH = Path(__file__).resolve().parent.parent / "datasets" / "rag_cases.json"


def run_rag_eval():
    print("=" * 65)
    print("RUNNING RAG & CRAG EVALUATION SUITE")
    print("=" * 65)

    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        cases = json.load(f)

    results = []
    total_start = time.time()

    for idx, case in enumerate(cases, 1):
        case_id = case["case_id"]
        query = case["query"]
        print(f"[{idx}/{len(cases)}] Evaluating {case_id} ('{query[:40]}...')...")

        start = time.time()
        try:
            crag_output = run_crag(query)
            duration = time.time() - start
            retrieved = crag_output.get("relevant_documents", [])
            status = crag_output.get("status")
            result = evaluate_rag_retrieval(
                case=case,
                retrieved_documents=retrieved,
                crag_status=status,
                latency_seconds=duration,
            )
        except Exception as exc:
            duration = time.time() - start
            result = EvalResult(
                case_id=case_id,
                passed=False,
                failures=[f"CRAG execution crashed: {str(exc)}"],
                latency_seconds=duration,
            )

        results.append(result)
        status_icon = " PASS" if result.passed else " FAIL"
        print(f"       -> {status_icon} ({duration:.2f}s) - {result.failures or 'OK'}")

    total_duration = time.time() - total_start
    passed_count = sum(1 for r in results if r.passed)
    pass_rate = (passed_count / len(results)) * 100 if results else 0
    hit_at_k_avg = (
        sum(float(r.metrics.get("hit_at_k", 0)) for r in results) / len(results)
        if results
        else 0
    )
    mrr_avg = (
        sum(float(r.metrics.get("mrr", 0)) for r in results) / len(results)
        if results
        else 0
    )

    print("\n" + "=" * 65)
    print("RAG & CRAG EVALUATION SUMMARY")
    print("=" * 65)
    print(f"Total Cases:     {len(results)}")
    print(f"Passed:          {passed_count}")
    print(f"Failed:          {len(results) - passed_count}")
    print(f"Pass Rate:       {pass_rate:.1f}%")
    print(f"Hit@4:           {hit_at_k_avg:.3f}")
    print(f"MRR:             {mrr_avg:.3f}")
    print(f"Total Runtime:   {total_duration:.2f}s")
    print("=" * 65 + "\n")

    return results


if __name__ == "__main__":
    run_rag_eval()
