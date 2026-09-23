from typing import Any

from app.rag.vectorstore import get_vector_store


DEFAULT_TOP_K = 4


def retrieve_policy_documents(
    query: str,
    top_k: int = DEFAULT_TOP_K,
) -> list[dict[str, Any]]:

    vector_store = get_vector_store()

    results = (
        vector_store.similarity_search_with_score(
            query=query,
            k=top_k,
        )
    )

    retrieved = []

    for document, score in results:

        retrieved.append(
            {
                "content": document.page_content,
                "source": document.metadata.get(
                    "source"
                ),
                "policy_id": document.metadata.get(
                    "policy_id"
                ),
                "title": document.metadata.get(
                    "title"
                ),
                "version": document.metadata.get(
                    "version"
                ),
                "category": document.metadata.get(
                    "category"
                ),
                "chunk_id": document.metadata.get(
                    "chunk_id"
                ),
                "score": float(score),
            }
        )

    return retrieved