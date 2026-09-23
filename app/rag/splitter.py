from langchain_core.documents import Document
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
)


def split_documents(
    documents: list[Document],
) -> list[Document]:

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=120,
    )

    all_chunks = []

    for document in documents:

        chunks = splitter.split_documents(
            [document]
        )

        source = document.metadata.get(
            "source",
            "unknown",
        )

        source_name = source.rsplit(
            ".",
            1,
        )[0]

        for index, chunk in enumerate(chunks):

            chunk.metadata["chunk_id"] = (
                f"{source_name}-{index:04d}"
            )

            all_chunks.append(chunk)

    return all_chunks