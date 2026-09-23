from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore

from app.config import settings
from app.rag.loader import (
    load_knowledge_documents,
)
from app.rag.splitter import split_documents
from app.rag import (
    COLLECTION_NAME,
)


def main():
    documents = load_knowledge_documents()

    print(
        f"Loaded {len(documents)} documents"
    )

    chunks = split_documents(documents)

    print(
        f"Created {len(chunks)} chunks"
    )

    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
    )

    QdrantVectorStore.from_documents(
        documents=chunks,
        embedding=embeddings,
        url=settings.qdrant_url,
        collection_name=COLLECTION_NAME,
        force_recreate=True,
    )

    print(
        "Knowledge base indexed successfully."
    )


if __name__ == "__main__":
    main()