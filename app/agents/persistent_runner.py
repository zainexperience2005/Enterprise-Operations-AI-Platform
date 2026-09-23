from typing import Any

from app.agents.orchestrator import (
    create_investigation_graph,
)
from app.memory.checkpointer import (
    create_checkpointer,
)


def run_persistent_investigation(
    request: str,
    thread_id: str,
) -> dict[str, Any]:

    config = {
        "configurable": {
            "thread_id": thread_id
        },
        "recursion_limit": 25,
    }

    with create_checkpointer() as checkpointer:

        graph = create_investigation_graph(
            checkpointer=checkpointer
        )

        return graph.invoke(
            {
                "request": request
            },
            config=config,
        )