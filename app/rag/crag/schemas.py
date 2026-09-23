from typing import Literal

from pydantic import BaseModel, Field


class RelevanceGrade(BaseModel):
    verdict: Literal[
        "relevant",
        "irrelevant",
    ]

    reason: str = Field(
        min_length=1
    )