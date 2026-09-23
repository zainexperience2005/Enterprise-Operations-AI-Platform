from app.agents.persistent_runner import (
    run_persistent_investigation,
)


result = run_persistent_investigation(
    request=(
        "Investigate the incorrect charge "
        "reported in TICK-4001."
    ),
    thread_id="investigation-TICK-4001",
)


print(
    result["final_resolution"]
)