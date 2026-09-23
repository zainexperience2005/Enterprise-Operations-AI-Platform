from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.config import settings


class EvidenceEvaluation(BaseModel):
    verdict: Literal[
        "sufficient",
        "insufficient",
    ]

    missing_information: list[str] = Field(
        default_factory=list
    )

    reason: str

    recommended_specialist: Literal[
        "api",
        "sql",
        "rag",
        "none",
    ]

    recommended_instruction: str | None = None


class LoopDecision(BaseModel):
    action: Literal[
        "finish",
        "correct",
        "stop",
    ]

    reason: str

    correction_type: Literal[
        "api",
        "sql",
        "rag",
        "none",
    ]

    instruction: str | None = None


EVALUATOR_PROMPT = """
You are an enterprise investigation evidence evaluator.

Determine whether the currently collected evidence is
sufficient to answer the original investigation request.

Rules:

1. Evaluate only the supplied evidence.
2. Do not invent missing facts.
3. Clearly identify missing evidence.
4. If more evidence could reasonably resolve the gap,
   recommend exactly one specialist:
   api, sql, or rag.
5. Do not execute tools.
6. Do not propose business mutations.
7. Historical memory is context, not current operational truth.
8. A failed dependency is not evidence that the requested
   record or policy does not exist.
"""

model = ChatOpenAI(
    model=settings.openai_model,
    temperature=0,
)

evaluation_model = model.with_structured_output(
    EvidenceEvaluation
)


def evaluate_evidence(
    request: str,
    evidence: str,
    errors: str,
) -> EvidenceEvaluation:
    prompt = f"""
Original investigation request:

{request}


Evidence collected:

{evidence}


Known failures/errors:

{errors}


Determine whether the evidence is sufficient.

If it is insufficient and another investigation step could
reasonably close the evidence gap, recommend one specialist
and one focused instruction.
"""

    return evaluation_model.invoke(
        [
            SystemMessage(content=EVALUATOR_PROMPT),
            HumanMessage(content=prompt),
        ]
    )
