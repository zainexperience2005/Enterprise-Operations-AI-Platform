from typing import Any, Union
from pydantic import BaseModel, Field


class EvalResult(BaseModel):
    case_id: str
    passed: bool
    metrics: dict[str, Union[float, bool, int, str]] = Field(default_factory=dict)
    failures: list[str] = Field(default_factory=list)
    latency_seconds: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)
