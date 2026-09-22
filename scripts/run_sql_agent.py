
from langchain_core.messages import HumanMessage

from app.agents.sql_agent import sql_agent_graph


def main():
    result = sql_agent_graph.invoke(
        {
            "messages": [
                HumanMessage(
                    content=(
                        "Investigate invoice INV-2001. "
                        "Compare its amount with the related "
                        "order total and explain any discrepancy."
                    )
                )
            ],
            "iterations": 0,
        }
    )

    print("\nFINAL RESPONSE\n")
    print(result["messages"][-1].content)


if __name__ == "__main__":
    main()