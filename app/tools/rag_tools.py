from langchain_core.tools import tool

from app.rag.crag.graph import run_crag
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
    result = run_crag(query)

    if result.get("status") == "insufficient":
        return {
            "status": "insufficient",
            "query": query,
            "evidence": [],
        }

    return {
        "status": "success",
        "query": query,
        "search_query": result.get("current_query", query),
        "rewrite_count": result.get("rewrite_count", 0),
        "evidence": result.get("relevant_documents", []),
    }