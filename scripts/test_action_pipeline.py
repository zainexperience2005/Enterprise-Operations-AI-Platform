"""Test script for Step 12: Controlled Actions, Human Approval & Safe Execution."""

from pprint import pprint
from langgraph.types import Command

from app.agents.orchestrator import create_investigation_graph
from app.memory.checkpointer import create_checkpointer


def main():
    thread_id = "test-action-TICK-4001-v1"
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 30,
    }

    print("=" * 60)
    print("STEP 1: RUN INVESTIGATION UNTIL HUMAN APPROVAL INTERRUPT")
    print("=" * 60)

    with create_checkpointer() as checkpointer:
        graph = create_investigation_graph(checkpointer=checkpointer)

        # 1. Initial invocation (should pause at approval interrupt)
        result = graph.invoke(
            {
                "request": (
                    "Customer reports being charged more than the original "
                    "order total in support ticket TICK-4001. Investigate and resolve."
                ),
                "investigation_id": "TICK-4001",
            },
            config=config,
        )

        state = graph.get_state(config)
        print("\n--- GRAPH STATE AFTER FIRST RUN ---")
        print("Next scheduled node:", state.next)
        if state.tasks:
            for task in state.tasks:
                if task.interrupts:
                    print("Interrupt Details:")
                    pprint(task.interrupts[0].value)

        # 2. If interrupted, simulate human decision to APPROVE
        if state.next and "approval" in state.next:
            print("\n" + "=" * 60)
            print("STEP 2: HUMAN APPROVER APPROVES ACTION VIA RESUME COMMAND")
            print("=" * 60)

            resumed_result = graph.invoke(
                Command(
                    resume={
                        "approved": True,
                        "approved_by": "finance_lead_zain",
                        "feedback": "Approved 200.00 refund following policy REF-001.",
                    }
                ),
                config=config,
            )

            print("\n--- RESUMED WORKFLOW RESULT ---")
            print("Approval Status:", resumed_result.get("approval_status"))
            print("Proposed Action:", resumed_result.get("proposed_action"))
            print("Action Result:")
            pprint(resumed_result.get("action_result"))


if __name__ == "__main__":
    main()
