from pprint import pprint

from app.rag.loader import (
    load_knowledge_documents,
)


documents = load_knowledge_documents()

for document in documents:
    print("\nDOCUMENT")
    pprint(document.metadata)

    print("\nCONTENT")
    print(document.page_content[:200])