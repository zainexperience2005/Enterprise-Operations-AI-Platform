from typing import Any
from evals.evaluators.schemas import EvalResult


def evaluate_rag_retrieval(
    case: dict[str, Any],
    retrieved_documents: list[dict[str, Any]],
    crag_status: str | None = None,
    latency_seconds: float = 0.0,
) -> EvalResult:
    """Evaluates RAG/CRAG retrieval precision, Hit@K, and abstention behavior.

    Metrics:
    - hit_at_k: Whether at least one expected source is present in top-k.
    - mrr: Mean Reciprocal Rank of the first relevant source.
    - correct_abstention: For unanswerable queries, whether CRAG returned 'insufficient'.
    """
    case_id = case.get("case_id", "RAG-UNKNOWN")
    answerable = case.get("answerable", True)
    expected_sources = set(case.get("expected_sources", []))
    expected_policy_ids = set(case.get("expected_policy_ids", []))

    failures = []
    hit_at_k = False
    mrr = 0.0

    if not answerable:
        # Expected behavior for unanswerable questions: crag_status == "insufficient"
        # or no relevant documents.
        is_abstention = (crag_status == "insufficient") or (len(retrieved_documents) == 0)
        if not is_abstention:
            failures.append("System failed to abstain on an unanswerable question!")
        passed = is_abstention
        return EvalResult(
            case_id=case_id,
            passed=passed,
            metrics={
                "answerable": False,
                "abstention_correct": is_abstention,
                "hit_at_k": 1.0 if is_abstention else 0.0,
                "mrr": 1.0 if is_abstention else 0.0,
            },
            failures=failures,
            latency_seconds=latency_seconds,
            metadata={"category": case.get("category", "unsupported")},
        )

    # For answerable questions:
    retrieved_sources = [doc.get("source") for doc in retrieved_documents]
    retrieved_policy_ids = [doc.get("policy_id") for doc in retrieved_documents]

    for rank, src in enumerate(retrieved_sources, start=1):
        if src in expected_sources:
            hit_at_k = True
            mrr = 1.0 / rank
            break

    if not hit_at_k and expected_sources:
        failures.append(f"Expected sources {expected_sources} not found in retrieved: {retrieved_sources}")

    passed = len(failures) == 0

    return EvalResult(
        case_id=case_id,
        passed=passed,
        metrics={
            "answerable": True,
            "hit_at_k": 1.0 if hit_at_k else 0.0,
            "mrr": mrr,
            "retrieved_count": len(retrieved_documents),
            "sources_matched": hit_at_k,
        },
        failures=failures,
        latency_seconds=latency_seconds,
        metadata={"category": case.get("category", "policy")},
    )
