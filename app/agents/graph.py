from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.agents.nodes import agent_node
from app.agents.state import AgentState
from app.tools.registry import ENTERPRISE_TOOLS

tool_node = ToolNode(ENTERPRISE_TOOLS)

MAX_ITERATIONS = 8


def should_continue(state: AgentState):
    if state.get("iterations", 0) >= MAX_ITERATIONS:
        return END

    last_message = state["messages"][-1]

    if last_message.tool_calls:
        return "tools"

    return END

builder = StateGraph(AgentState)

builder.add_node(
    "agent",
    agent_node,
)

builder.add_node(
    "tools",
    tool_node,
)

builder.add_edge(
    START,
    "agent",
)

builder.add_conditional_edges(
    "agent",
    should_continue,
    {
        "tools": "tools",
        END: END,
    },
)

builder.add_edge(
    "tools",
    "agent",
)

graph = builder.compile()