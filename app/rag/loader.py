from pathlib import Path
import re

import yaml
from langchain_core.documents import Document


KNOWLEDGE_DIR = Path("data/knowledge")


def parse_markdown_file(
    path: Path,
) -> Document:

    raw_text = path.read_text(
        encoding="utf-8"
    )

    metadata = {
        "source": path.name,
    }

    content = raw_text

    match = re.match(
        r"^---[^\n]*\r?\n(.*?)\r?\n---\s*(?:\r?\n|$)",
        raw_text,
        re.DOTALL,
    )

    if match:
        front_matter = match.group(1)
        content = raw_text[match.end():].strip()

        parsed_metadata = (
            yaml.safe_load(front_matter)
            or {}
        )

        if isinstance(parsed_metadata, dict):
            metadata.update(
                parsed_metadata
            )

    return Document(
        page_content=content,
        metadata=metadata,
    )


def load_knowledge_documents() -> list[Document]:

    documents = []

    for path in KNOWLEDGE_DIR.glob("*.md"):
        documents.append(
            parse_markdown_file(path)
        )

    return documents