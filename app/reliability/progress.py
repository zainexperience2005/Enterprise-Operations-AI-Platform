import hashlib
import json
from typing import Any


def evidence_fingerprint(
    evidence: list[dict[str, Any]],
) -> str:
    """Generate a deterministic SHA-256 hash of accumulated evidence.

    Used by the orchestrator to detect stagnation across loop iterations.
    """
    normalized = json.dumps(
        evidence,
        sort_keys=True,
        default=str,
    )

    return hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()
