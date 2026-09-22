"""Script to execute an end-to-end multi-agent investigation.

Coordinates Planner, Specialist Agents (API & SQL), and the Resolution Analyst
to investigate a sample support ticket (TICK-4001).
"""

import sys
from pathlib import Path
from pprint import pprint

# Ensure workspace root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.orchestrator import investigation_graph


def main():
    """Run investigation graph for an incorrect invoice charge complaint."""
    # Run the full investigation pipeline
    result = investigation_graph.invoke(
        {
            "request": (
                "Customer reported an incorrect charge "
                "in support ticket TICK-4001. "
                "Investigate what happened."
            )
        },
        config={
            "recursion_limit": 25,
        },
    )

    print("\n" + "=" * 60)
    print("INVESTIGATION PLAN")
    print("=" * 60)
    pprint(
        result["plan"].model_dump()
    )

    print("\n" + "=" * 60)
    print("COLLECTED EVIDENCE")
    print("=" * 60)
    pprint(
        result["evidence"]
    )

    if result.get("errors"):
        print("\n" + "=" * 60)
        print("ERRORS LOGGED")
        print("=" * 60)
        pprint(result["errors"])

    print("\n" + "=" * 60)
    print("FINAL RESOLUTION")
    print("=" * 60)
    print(
        result["final_resolution"]
    )


if __name__ == "__main__":
    main()