"""Enterprise Reliability Error Taxonomy.

Classifies system and agent failures into Transient/Retryable vs Permanent
categories to prevent wasteful retries and support graceful degradation.
"""


class PlatformError(Exception):
    """Base exception for all enterprise platform errors."""


class RetryableError(PlatformError):
    """Transient failure where retrying with backoff may succeed."""


class PermanentError(PlatformError):
    """Deterministic failure where retrying is futile and should fail immediately."""


class DependencyUnavailableError(RetryableError):
    """An external dependency (API, Database, Qdrant, LLM) is temporarily unreachable."""


class ValidationError(PermanentError):
    """Request payload, parameters, or schema validation failed."""


class AuthorizationError(PermanentError):
    """Action or query violates security policies or requires ungranted approval."""


class BudgetExceededError(PermanentError):
    """Investigation exceeded maximum iteration or computational budget."""
