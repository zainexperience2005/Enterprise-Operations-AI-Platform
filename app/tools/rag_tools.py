from langchain_core.tools import tool

from app.rag.retriever import (
    retrieve_policy_documents,
)
from app.tools.schemas import PolicySearchInput


@tool(args_schema=PolicySearchInput)
def search_enterprise_knowledge(
    query: str,
) -> dict:
    """
    Search enterprise policies, procedures and SOPs.

    Use this tool when an investigation requires policy,
    eligibility, approval or procedural evidence.
    """

    results = retrieve_policy_documents(
        query=query
    )

    return {
        "success": True,
        "query": query,
        "results": results,
    }