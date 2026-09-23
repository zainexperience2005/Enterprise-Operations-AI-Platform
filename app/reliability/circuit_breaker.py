"""Circuit Breaker Implementation.

Protects external enterprise dependencies from cascading failures during outages
by transitioning across CLOSED, OPEN, and HALF_OPEN states.
"""

import time


class CircuitOpenError(Exception):
    """Raised when an operation is attempted while the circuit breaker is OPEN."""


class CircuitBreaker:
    """Stateful circuit breaker guarding external service calls."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_seconds: float = 30.0,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds

        self.failure_count = 0
        self.opened_at: float | None = None

    @property
    def state(self) -> str:
        """Current circuit state: 'CLOSED', 'OPEN', or 'HALF_OPEN'."""
        if self.opened_at is None:
            return "CLOSED"

        elapsed = time.monotonic() - self.opened_at
        if elapsed >= self.recovery_seconds:
            return "HALF_OPEN"

        return "OPEN"

    def allow_request(self) -> bool:
        """Check if a new request is permitted to proceed."""
        current_state = self.state
        if current_state == "OPEN":
            return False

        return True

    def record_success(self) -> None:
        """Record a successful execution, resetting failure counters."""
        self.failure_count = 0
        self.opened_at = None

    def record_failure(self) -> None:
        """Record an operation failure and trip to OPEN if threshold is reached."""
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.opened_at = time.monotonic()
