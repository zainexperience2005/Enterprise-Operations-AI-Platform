from pprint import pprint

from app.rag.retriever import (
    retrieve_policy_documents,
)


results = retrieve_policy_documents(
    (
        "What should happen when an invoice "
        "is higher than the approved order total?"
    )
)


pprint(results)