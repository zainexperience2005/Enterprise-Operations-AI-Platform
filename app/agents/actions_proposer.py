from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.actions.schemas import ProposedAction

class ActionProposal(BaseModel):
    should_act: bool

    action: ProposedAction | None = None

    explanation: str

ACTION_PROPOSER_PROMPT = """
You are an enterprise action proposal agent.

Your job is to propose a business action only when the
investigation evidence and resolution support it.

Rules:

1. Never claim an action has already been executed.
2. Never approve your own action.
3. Never invent invoice identifiers or monetary amounts.
4. Use only the supplied investigation evidence.
5. The refund amount must be supported by the evidence.
6. If a safe action cannot be established from the evidence,
   do not fabricate one.
"""


model = ChatOpenAI(
    model="gpt-5.1",
    temperature=0,
)


structured_model = model.with_structured_output(
    ActionProposal
)



def propose_action(
    request: str,
    evidence: str,
    resolution: str,
) -> ActionProposal:

    prompt = f"""
Original request:

{request}


Investigation evidence:

{evidence}


Investigation resolution:

{resolution}


Determine whether a business action should be proposed.
"""

    return structured_model.invoke(
        [
            SystemMessage(
                content=ACTION_PROPOSER_PROMPT
            ),
            HumanMessage(
                content=prompt
            ),
        ]
    )