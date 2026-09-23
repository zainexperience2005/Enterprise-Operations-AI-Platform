from pathlib import Path

from langchain_core.documents import Document


KNOWLEDGE_DIR = Path("data/knowledge")


def load_knowledge_documents() -> list[Document]:
    documents = []

    for path in KNOWLEDGE_DIR.glob("*.md"):
        text = path.read_text(
            encoding="utf-8"
        )

        document = Document(
            page_content=text,
            metadata={
                "source": path.name,
            },
        )

        documents.append(document)

    return documents