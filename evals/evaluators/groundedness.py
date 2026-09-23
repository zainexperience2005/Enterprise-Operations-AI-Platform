from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.config import settings
from evals.evaluators.schemas import EvalResult


class GroundednessEvaluation(BaseModel):
    grounded: bool = Field(
        description="Whether every material factual claim in the answer is supported by the supplied evidence."
    )
    unsupported_claims: list[str] = Field(
        default_factory=list,
        description="List of specific factual claims in the answer that lack evidence support.",
    )
    reason: str = Field(
        description="Detailed explanation justifying the groundedness decision."
    )


GROUNDEDNESS_JUDGE_PROMPT = """
You are an expert factual groundedness evaluator for enterprise AI systems.

Your task is to determine whether every material factual claim in the supplied answer
is strictly supported by the provided evidence.

Strict Rules:
1. Do not use outside knowledge or assumptions. Evaluate ONLY against the supplied evidence.
2. If the answer contains a factual claim (e.g., numbers, policy limits, dates, customer status)
   not directly supported by the evidence, mark grounded = false and quote the unsupported claim.
3. If the answer appropriately states that information is unknown or unretrieved, and makes no
   unsupported assertions, mark grounded = true.
4. Do not evaluate writing style or tone—only factual adherence to evidence.
"""

model = ChatOpenAI(
    model=settings.openai_model,
    temperature=0,
)

judge_model = model.with_structured_output(GroundednessEvaluation)


def evaluate_groundedness(
    case_id: str,
    evidence: str,
    answer: str,
    latency_seconds: float = 0.0,
) -> EvalResult:
    """Invokes LLM-as-a-judge to evaluate whether an answer is strictly grounded in evidence."""
    human_prompt = f"""
Provided Evidence:
<evidence>
{evidence}
</evidence>

AI Answer to Evaluate:
<answer>
{answer}
</answer>

Determine whether the answer is strictly grounded in the evidence.
"""
    try:
        evaluation: GroundednessEvaluation = judge_model.invoke(
            [
                SystemMessage(content=GROUNDEDNESS_JUDGE_PROMPT),
                HumanMessage(content=human_prompt),
            ]
        )
        passed = evaluation.grounded
        failures = evaluation.unsupported_claims if not passed else []
        reason = evaluation.reason
    except Exception as exc:
        passed = False
        failures = [f"Groundedness judge execution failed: {str(exc)}"]
        reason = str(exc)

    return EvalResult(
        case_id=case_id,
        passed=passed,
        metrics={
            "grounded": passed,
            "unsupported_claim_count": len(failures),
        },
        failures=failures,
        latency_seconds=latency_seconds,
        metadata={"reason": reason},
    )
