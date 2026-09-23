from langchain_openai import ChatOpenAI

from app.tools.registry import ENTERPRISE_TOOLS


model = ChatOpenAI(
    model="gpt-5.1",
    temperature=0,
)


model_with_tools = model.bind_tools(
    ENTERPRISE_TOOLS
)

