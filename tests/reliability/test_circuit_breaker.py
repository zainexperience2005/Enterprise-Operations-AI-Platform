import time
from app.reliability.circuit_breaker import CircuitBreaker


def test_circuit_breaker_initial_closed_state():
    """Circuit breaker should start in CLOSED state and permit requests."""
    cb = CircuitBreaker(failure_threshold=3, recovery_seconds=0.2)
    assert cb.state == "CLOSED"
    assert cb.allow_request() is True


def test_circuit_breaker_trips_to_open_on_threshold():
    """Circuit breaker should trip to OPEN state once failure threshold is reached."""
    cb = CircuitBreaker(failure_threshold=3, recovery_seconds=0.2)

    cb.record_failure()
    assert cb.state == "CLOSED"
    assert cb.allow_request() is True

    cb.record_failure()
    assert cb.state == "CLOSED"

    # 3rd failure reaches threshold
    cb.record_failure()
    assert cb.state == "OPEN"
    assert cb.allow_request() is False


def test_circuit_breaker_transitions_to_half_open_and_recovers():
    """Circuit breaker should transition to HALF_OPEN after cooldown and reset upon success."""
    cb = CircuitBreaker(failure_threshold=2, recovery_seconds=0.1)

    cb.record_failure()
    cb.record_failure()
    assert cb.state == "OPEN"
    assert cb.allow_request() is False

    # Wait for recovery period to elapse
    time.sleep(0.15)
    assert cb.state == "HALF_OPEN"
    assert cb.allow_request() is True

    # Success in half-open state resets circuit
    cb.record_success()
    assert cb.state == "CLOSED"
    assert cb.failure_count == 0
    assert cb.allow_request() is True
