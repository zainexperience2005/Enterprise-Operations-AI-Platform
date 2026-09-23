import json
from pathlib import Path

from app.rag.retriever import (
    retrieve_policy_documents,
)


DATASET_PATH = Path(
    "evals/rag/retrieval_cases.json"
)


def load_cases():
    return json.loads(
        DATASET_PATH.read_text(
            encoding="utf-8"
        )
    )


def evaluate_case(
    case: dict,
    top_k: int = 4,
) -> dict:

    results = retrieve_policy_documents(
        query=case["query"],
        top_k=top_k,
    )

    retrieved_sources = [
        item["source"]
        for item in results
    ]

    expected_sources = case[
        "expected_sources"
    ]

    hit = any(
        source in retrieved_sources
        for source in expected_sources
    )
    reciprocal_rank = 0.0

    for rank, source in enumerate(
        retrieved_sources,
        start=1,
    ):
        if source in expected_sources:
            reciprocal_rank = 1 / rank
            break

    return {
        "case_id": case["case_id"],
        "query": case["query"],
        "expected_sources": expected_sources,
        "retrieved_sources": retrieved_sources,
        "hit": hit,
        "reciprocal_rank": reciprocal_rank,
    }


def main():

    cases = load_cases()

    results = [
        evaluate_case(case)
        for case in cases
    ]

    successful = sum(
        result["hit"]
        for result in results
    )

    hit_rate = (
        successful / len(results)
        if results
        else 0
    )
    mrr = (
    sum(
        result["reciprocal_rank"]
        for result in results
    )
    / len(results)
    if results
    else 0
    )
    for result in results:
        print(
            result["case_id"],
            "PASS" if result["hit"] else "FAIL",
        )

        print(
            "Expected:",
            result["expected_sources"],
        )

        print(
            "Retrieved:",
            result["retrieved_sources"],
        )

        print()

    print(
        f"Hit Rate@4: {hit_rate:.2%}"
    )
    print(
        f"Mean Reciprocal Rank: {mrr:.2f}"
    )


if __name__ == "__main__":
    main()