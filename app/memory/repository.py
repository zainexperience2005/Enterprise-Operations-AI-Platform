from sqlalchemy import select

from app.db.models import (
    InvestigationMemory,
)
from app.db.session import SessionLocal


def save_memory(
    investigation_id: str,
    memory_type: str,
    content: str,
) -> InvestigationMemory:

    with SessionLocal() as session:

        memory = InvestigationMemory(
            investigation_id=investigation_id,
            memory_type=memory_type,
            content=content,
        )

        session.add(memory)

        session.commit()
        session.refresh(memory)

        return memory


def get_investigation_memories(
    investigation_id: str,
) -> list[InvestigationMemory]:

    with SessionLocal() as session:

        statement = (
            select(InvestigationMemory)
            .where(
                InvestigationMemory.investigation_id
                == investigation_id
            )
            .order_by(
                InvestigationMemory.created_at
            )
        )

        return list(
            session.scalars(statement)
        )