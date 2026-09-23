from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
)
from langchain_openai import ChatOpenAI

from app.config import settings


REWRITE_PROMPT = """
You rewrite enterprise knowledge-base search queries.

Rewrite the user's query so it is more effective for
retrieving relevant policies, SOPs, procedures, or rules.

Rules:

- Preserve the original intent.
- Do not answer the question.
- Do not invent facts.
- Produce only the improved search query.
"""


model = ChatOpenAI(
    model=settings.openai_model,
    temperature=0,
)


def rewrite_query(
    original_query: str,
) -> str:

    response = model.invoke(
        [
            SystemMessage(
                content=REWRITE_PROMPT
            ),
            HumanMessage(
                content=original_query
            ),
        ]
    )

    return str(response.content).strip()
