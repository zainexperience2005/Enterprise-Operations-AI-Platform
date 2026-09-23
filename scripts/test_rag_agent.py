from app.agents.rag_agent import (
    run_rag_specialist,
)


result = run_rag_specialist(
    """
    Find the enterprise policy governing a situation
    where a customer paid more than the approved
    order amount.

    Explain the relevant policy and cite the source.
    """
)


print(result)