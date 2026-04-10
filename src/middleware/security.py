"""Security middleware for the API.

Handles:
- API key validation for dashboard/client access
- Webhook authentication validation (HMAC and shared-secret) for Vapi callbacks
- PII redaction in logs
- Basic rate limiting
"""

from __future__ import annotations

import hashlib
import hmac
import re
import time
from collections import defaultdict
from typing import Any

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from src.config.settings import settings


# --- PII Redaction ---

# Patterns for common PII in log output
PII_PATTERNS = [
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN_REDACTED]"),  # SSN
    (re.compile(r"\b\d{9}\b"), "[SSN_REDACTED]"),  # SSN without dashes
    (re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"), "[PHONE_REDACTED]"),  # Phone
    (
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
        "[EMAIL_REDACTED]",
    ),
]


def redact_pii(text: str) -> str:
    """Redact PII patterns from text for safe logging.

    This is a defense-in-depth measure. PII should not appear in logs,
    but if it does, this function masks it.
    """
    for pattern, replacement in PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


# --- Webhook Signature Validation ---


def validate_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Validate HMAC-SHA256 signature on incoming webhooks.

    This prevents webhook spoofing — only Vapi (who knows the secret)
    can send valid webhooks to our endpoint.

    Args:
        payload: Raw request body bytes.
        signature: The signature from the request header.
        secret: The shared webhook secret.

    Returns:
        True if the signature is valid. Returns False if no secret
        or signature was provided — the caller must decide how to
        handle unauthenticated webhooks based on environment.
    """
    if not secret or not signature:
        return False

    expected = hmac.new(
        secret.encode(), payload, hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


def validate_webhook_secret(secret_header: str, auth_header: str, secret: str) -> bool:
    """Validate shared-secret webhook authentication.

    Supports:
    - `x-vapi-secret: <secret>`
    - `Authorization: Bearer <secret>`

    Args:
        secret_header: Value of x-vapi-secret header.
        auth_header: Value of Authorization header.
        secret: Shared webhook secret configured in both systems.

    Returns:
        True when either auth mode matches the configured secret.
        Returns False if no secret is configured — the caller must
        decide how to handle missing-secret scenarios.
    """
    if not secret:
        return False

    if secret_header and hmac.compare_digest(secret_header, secret):
        return True

    if auth_header:
        scheme, _, value = auth_header.partition(" ")
        if scheme.lower() == "bearer" and value and hmac.compare_digest(
            value.strip(), secret
        ):
            return True

    return False


# --- API Key Middleware ---


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Validates API key on all non-webhook, non-health endpoints.

    The API key is sent in the X-API-Key header. Webhook endpoints use
    webhook-specific authentication instead.
    """

    # Paths that don't require API key auth
    EXEMPT_PATHS = {"/health", "/docs", "/openapi.json", "/webhooks/vapi"}

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip auth for CORS preflight requests
        if request.method == "OPTIONS":
            return await call_next(request)

        # Skip auth for exempt paths
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        # No API key configured: fail closed in production, fail open in dev.
        # This lets local development work without ceremony while preventing
        # a misconfigured production deploy from exposing the API.
        #
        # Note: BaseHTTPMiddleware does not propagate HTTPException to the
        # app's exception handlers, so we return JSONResponse directly.
        if not settings.api_key:
            if settings.is_production:
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={"detail": "API authentication not configured"},
                )
            return await call_next(request)

        api_key = request.headers.get("X-API-Key", "")
        if not hmac.compare_digest(api_key, settings.api_key):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid or missing API key"},
            )

        return await call_next(request)


# --- Rate Limiting ---


class RateLimiter:
    """Simple in-memory rate limiter for POC.

    For production, use Redis-backed rate limiting.
    """

    def __init__(self, max_requests: int = 60, window_seconds: int = 60) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, client_id: str) -> bool:
        """Check if a client is within their rate limit."""
        now = time.time()
        window_start = now - self._window_seconds

        # Clean old entries
        self._requests[client_id] = [
            t for t in self._requests[client_id] if t > window_start
        ]

        if len(self._requests[client_id]) >= self._max_requests:
            return False

        self._requests[client_id].append(now)
        return True


# Singleton rate limiter
rate_limiter = RateLimiter()
