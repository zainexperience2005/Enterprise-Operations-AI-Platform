from langchain_core.messages import SystemMessage

from app.agents.model import model_with_tools
from app.agents.prompts import SYSTEM_PROMPT
from app.agents.state import AgentState


def agent_node(state: AgentState):
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        *state["messages"],
    ]

    response = model_with_tools.invoke(messages)

    return {
        "messages": [response],
        "iterations": state.get("iterations", 0) + 1,
    }