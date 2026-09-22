from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.agents.state import AgentState
from app.tools.sql_tools import SQL_TOOLS


SQL_SYSTEM_PROMPT = """
You are the SQL Investigation Specialist for an enterprise
operations platform.

Your responsibility is to investigate structured enterprise
data using safe read-only SQL.

Rules:

1. Use inspect_database_schema when schema details are uncertain.
2. Only request SELECT queries.
3. Never request INSERT, UPDATE, DELETE, DROP, ALTER, CREATE,
   TRUNCATE or other mutations.
4. Use only tables and columns exposed by the schema tool.
5. Prefer focused queries over SELECT *.
6. Base conclusions only on returned query evidence.
7. Never invent database values.
8. If evidence is insufficient, state what is missing.
9. Do not recommend or execute business mutations.
10. Keep the final result evidence-based.
"""


sql_model = ChatOpenAI(
    model="gpt-5.1",
    temperature=0,
).bind_tools(SQL_TOOLS)


def sql_agent_node(state: AgentState):
    messages = [
        SystemMessage(content=SQL_SYSTEM_PROMPT),
        *state["messages"],
    ]

    response = sql_model.invoke(messages)

    return {
        "messages": [response],
        "iterations": state.get("iterations", 0) + 1,
    }


sql_tool_node = ToolNode(SQL_TOOLS)


MAX_SQL_ITERATIONS = 6


def route_sql_agent(state: AgentState):
    if state.get("iterations", 0) >= MAX_SQL_ITERATIONS:
        return END

    last_message = state["messages"][-1]

    if last_message.tool_calls:
        return "tools"

    return END


builder = StateGraph(AgentState)

builder.add_node(
    "sql_agent",
    sql_agent_node,
)

builder.add_node(
    "tools",
    sql_tool_node,
)

builder.add_edge(
    START,
    "sql_agent",
)

builder.add_conditional_edges(
    "sql_agent",
    route_sql_agent,
    {
        "tools": "tools",
        END: END,
    },
)

builder.add_edge(
    "tools",
    "sql_agent",
)

sql_agent_graph = builder.compile()