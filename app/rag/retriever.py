from typing import Any

from app.rag.vectorstore import get_vector_store


DEFAULT_TOP_K = 4


def retrieve_policy_documents(
    query: str,
    top_k: int = DEFAULT_TOP_K,
) -> list[dict[str, Any]]:

    vector_store = get_vector_store()

    documents = vector_store.similarity_search(
        query=query,
        k=top_k,
    )

    return [
        {
            "content": document.page_content,
            "source": document.metadata.get(
                "source"
            ),
            "chunk_id": document.metadata.get(
                "chunk_id"
            ),
        }
        for document in documents
    ]