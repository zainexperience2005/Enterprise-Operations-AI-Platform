from typing import Any

from pydantic import BaseModel, Field


class SpecialistResult(BaseModel):
    success: bool

    specialist: str

    summary: str

    evidence: list[dict[str, Any]] = Field(
        default_factory=list
    )

    errors: list[str] = Field(
        default_factory=list
    )

    degraded: bool = False