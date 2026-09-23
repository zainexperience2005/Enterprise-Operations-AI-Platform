from pprint import pprint

from app.rag.retriever import (
    retrieve_policy_documents,
)


results = retrieve_policy_documents(
    (
        "How many vacation days do software engineers receive?"
    )
)


pprint(results)