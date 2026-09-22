"""Script to test structured investigation planning.

Evaluates the Planner Agent's ability to decompose a customer inquiry
into typed, sequential specialist steps.
"""

import sys
from pathlib import Path
from pprint import pprint

# Ensure workspace root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.planner.planner import (
    create_investigation_plan,
)


def main():
    """Generate and display a structured investigation plan."""
    sample_request = (
        "Customer reported an incorrect charge in "
        "support ticket TICK-4001. Investigate it."
    )
    print(f"Generating plan for request: '{sample_request}'\n")

    plan = create_investigation_plan(sample_request)

    pprint(plan.model_dump())


if __name__ == "__main__":
    main()