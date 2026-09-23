from typing import TypedDict

from langgraph.graph import (
    END,
    START,
    StateGraph,
)

from app.rag.crag.grader import (
    grade_retrieved_documents,
)
from app.rag.crag.rewrite import (
    rewrite_query,
)
from app.rag.retriever import (
    retrieve_policy_documents,
)


class CRAGState(TypedDict, total=False):
    original_query: str
    current_query: str
    retrieved_documents: list[dict]
    relevant_documents: list[dict]
    rejected_documents: list[dict]
    rewrite_count: int
    status: str


MAX_REWRITES = 2


def retrieve_node(
    state: CRAGState,
):
    query = state.get(
        "current_query"
    ) or state["original_query"]

    documents = retrieve_policy_documents(
        query=query,
        top_k=4,
    )

    return {
        "current_query": query,
        "retrieved_documents": documents,
    }


def grade_node(
    state: CRAGState,
):
    relevant, rejected = grade_retrieved_documents(
        query=state["original_query"],
        documents=state.get("retrieved_documents", []),
    )

    return {
        "relevant_documents": relevant,
        "rejected_documents": rejected,
    }


def route_after_grading(
    state: CRAGState,
) -> str:
    relevant = state.get(
        "relevant_documents",
        [],
    )
    rewrite_count = state.get(
        "rewrite_count",
        0,
    )

    if relevant:
        return "complete"

    if rewrite_count >= MAX_REWRITES:
        return "insufficient"

    return "rewrite"


def rewrite_node(
    state: CRAGState,
):
    rewritten = rewrite_query(
        state.get("current_query") or state["original_query"]
    )

    return {
        "current_query": rewritten,
        "rewrite_count": (
            state.get(
                "rewrite_count",
                0,
            )
            + 1
        ),
    }


def complete_node(
    state: CRAGState,
):
    return {
        "status": "relevant"
    }


def insufficient_node(
    state: CRAGState,
):
    return {
        "status": "insufficient"
    }


builder = StateGraph(CRAGState)

builder.add_node(
    "retrieve",
    retrieve_node,
)

builder.add_node(
    "grade",
    grade_node,
)

builder.add_node(
    "rewrite",
    rewrite_node,
)

builder.add_node(
    "complete",
    complete_node,
)

builder.add_node(
    "insufficient",
    insufficient_node,
)

builder.add_edge(
    START,
    "retrieve",
)

builder.add_edge(
    "retrieve",
    "grade",
)

builder.add_conditional_edges(
    "grade",
    route_after_grading,
    {
        "complete": "complete",
        "rewrite": "rewrite",
        "insufficient": "insufficient",
    },
)

builder.add_edge(
    "rewrite",
    "retrieve",
)

builder.add_edge(
    "complete",
    END,
)

builder.add_edge(
    "insufficient",
    END,
)

crag_graph = builder.compile()


def run_crag(
    query: str,
) -> dict:
    return crag_graph.invoke(
        {
            "original_query": query,
            "current_query": query,
            "rewrite_count": 0,
        },
        config={
            "recursion_limit": 15
        },
    )
