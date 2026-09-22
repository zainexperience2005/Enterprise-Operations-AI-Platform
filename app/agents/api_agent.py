"""Enterprise API Specialist Agent.

Executes direct REST API integrations for customer, order, billing, and support
records using LangGraph ReAct tool-calling loop.
"""

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from app.tools.registry import ENTERPRISE_TOOLS

# System instructions guiding the API specialist agent
API_SYSTEM_PROMPT = """
You are the Enterprise API Investigation Specialist.

You retrieve factual records from enterprise APIs.

Available capabilities include customer, order, invoice
and support-ticket retrieval.

Rules:

1. Use tools for enterprise facts.
2. Never invent records.
3. Never claim a tool succeeded when it failed.
4. Perform investigation only.
5. Do not perform business mutations.
6. Return concise evidence useful to another agent.
"""

# Bind enterprise REST API tools to the language model
api_model = ChatOpenAI(
    model="gpt-5.1",
    temperature=0,
).bind_tools(ENTERPRISE_TOOLS)


def api_agent_node(state: MessagesState) -> dict:
    """Agent node that analyzes user instruction and generates tool calls or response."""
    response = api_model.invoke(
        [
            SystemMessage(
                content=API_SYSTEM_PROMPT
            ),
            *state["messages"],
        ]
    )

    return {
        "messages": [response]
    }


def route_api_agent(state: MessagesState) -> str:
    """Determine whether the agent requested tool execution or finished its investigation."""
    last_message = state["messages"][-1]

    if last_message.tool_calls:
        return "tools"

    return END


# Build the specialist graph using LangGraph
builder = StateGraph(MessagesState)

# Nodes: agent LLM decision and tool execution
builder.add_node(
    "api_agent",
    api_agent_node,
)
builder.add_node(
    "tools",
    ToolNode(ENTERPRISE_TOOLS),
)

# Edges: START -> api_agent -> [tools <-> api_agent] -> END
builder.add_edge(
    START,
    "api_agent",
)

builder.add_conditional_edges(
    "api_agent",
    route_api_agent,
    {
        "tools": "tools",
        END: END,
    },
)

builder.add_edge(
    "tools",
    "api_agent",
)

# Compile compiled graph for invocation
api_agent_graph = builder.compile()


def run_api_specialist(instruction: str) -> str:
    """Execute an API investigation task and return concise findings.

    Args:
        instruction: Investigation instruction and contextual evidence.

    Returns:
        str: Factual string content containing API findings or failure description.
    """
    result = api_agent_graph.invoke(
        {
            "messages": [
                HumanMessage(content=instruction)
            ]
        },
        config={
            "recursion_limit": 10
        },
    )

    return str(
        result["messages"][-1].content
    )