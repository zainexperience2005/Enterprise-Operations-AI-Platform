import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.messages import HumanMessage

from app.agents.graph import graph


def main():
    result = graph.invoke(
        {
            "messages": [
                HumanMessage(
                    content=("Investigate invoice INV-2001. "
                             "Determine whether the billed amount matches "
                             "the related order ORD-1001.")
                )
            ],
            "iterations": 0
        }
    )

    print("\nFINAL RESPONSE\n")

    print(
        result["messages"][-1].content
        
    )


if __name__ == "__main__":
    main()