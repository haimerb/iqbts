"""Helpers to authenticate against the iqoptionapi service."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

try:
    from iqoptionapi.stable_api import IQ_Option  # type: ignore[import-not-found]
except ImportError as exc:  # pragma: no cover - triggered only when dependency is missing
    raise ImportError(
        "The iqoptionapi package is required to use the IQ Option authentication service. "
        "Install it with 'pip install iqoptionapi' or ensure the dependency is available."
    ) from exc


logger = logging.getLogger(__name__)


class IQOptionAuthenticationError(RuntimeError):
    """Raised when the IQ Option API rejects the supplied credentials."""


@dataclass(slots=True)
class IQOptionAuthResult:
    """Captures the outcome of an IQ Option authentication attempt."""

    success: bool
    reason: Optional[str]
    client: Optional[IQ_Option]


def authenticate(
    email: str,
    password: str,
    *,
    enable_library_logging: bool = False,
    log_level: int = logging.INFO,
    log_format: str = "%(asctime)s %(levelname)s %(message)s",
) -> IQOptionAuthResult:
    """Attempt to authenticate against IQ Option using the supplied credentials."""

    if enable_library_logging:
        logging.basicConfig(level=log_level, format=log_format)

    client = IQ_Option(email, password)
    success, reason = client.connect()

    if success:
        logger.debug("IQ Option authentication succeeded for %s", email)
        return IQOptionAuthResult(True, reason, client)

    # The returned IQ_Option client remains active so the caller can decide when to close it.

    logger.warning("IQ Option authentication failed for %s: %s", email, reason)
    return IQOptionAuthResult(False, reason, None)


def authenticate_or_raise(
    email: str,
    password: str,
    **kwargs,
) -> IQ_Option:
    """Authenticate and return an IQ Option client, raising when authentication fails."""

    result = authenticate(email, password, **kwargs)
    if not result.success:
        message = result.reason or "Unknown authentication error"
        raise IQOptionAuthenticationError(message)
    return result.client  # type: ignore[return-value]


__all__ = [
    "IQOptionAuthResult",
    "IQOptionAuthenticationError",
    "authenticate",
    "authenticate_or_raise",
]
