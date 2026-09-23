from app.memory.repository import (
    get_investigation_memories,
    save_memory,
)


def load_memory_context(
    investigation_id: str,
) -> list[dict]:

    memories = get_investigation_memories(
        investigation_id
    )

    return [
        {
            "memory_type": memory.memory_type,
            "content": memory.content,
            "created_at": (
                memory.created_at.isoformat()
            ),
        }
        for memory in memories
    ]


def save_resolution_memory(
    investigation_id: str,
    resolution: str,
):
    return save_memory(
        investigation_id=investigation_id,
        memory_type="resolution",
        content=resolution,
    )