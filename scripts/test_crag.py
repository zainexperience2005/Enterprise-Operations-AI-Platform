from pprint import pprint

from app.rag.crag.graph import run_crag


def test_query(title: str, query: str):
    print("=" * 60)
    print(f"TEST: {title}")
    print("=" * 60)

    result = run_crag(query)

    print("Status:", result.get("status"))
    print("Original:", result.get("original_query"))
    print("Final query:", result.get("current_query"))
    print("Rewrites:", result.get("rewrite_count"))

    print("\nRelevant documents:")
    for document in result.get("relevant_documents", []):
        pprint(
            {
                "policy_id": document.get("policy_id"),
                "source": document.get("source"),
                "chunk_id": document.get("chunk_id"),
                "reason": document.get("relevance_reason"),
            }
        )

    print("\nRejected documents:")
    for document in result.get("rejected_documents", []):
        pprint(
            {
                "policy_id": document.get("policy_id"),
                "source": document.get("source"),
                "chunk_id": document.get("chunk_id"),
                "reason": document.get("relevance_reason"),
            }
        )
    print("\n")


if __name__ == "__main__":
    # 14.19 Test successful retrieval
    test_query(
        "Direct Relevant Query",
        "When does a refund require human approval?",
    )

    # 14.20 Test weak query needing rewriting
    test_query(
        "Weak Query Needing Correction",
        "What do we do about the extra money?",
    )

    # 14.21 Test unsupported question
    test_query(
        "Unsupported Query Requiring Insufficient Status",
        "How many annual vacation days do engineers receive?",
    )
