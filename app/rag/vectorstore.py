from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore

from app.config import settings


COLLECTION_NAME = "enterprise_policies"


embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
)


def get_vector_store() -> QdrantVectorStore:
    return QdrantVectorStore.from_existing_collection(
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        url=settings.qdrant_url,
    )