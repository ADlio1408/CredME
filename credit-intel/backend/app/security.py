"""
Minimal auth for the prototype: a shared API key passed via the
X-API-Key header, checked with a constant-time comparison.

This is intentionally simple for a hackathon prototype. The README's
"Next steps" section describes upgrading this to OAuth2 / JWT with
per-user scopes for a real deployment - swapping is localized to this
file because every route depends on `require_api_key`, not on ad-hoc
checks scattered through the codebase.
"""
import hmac

from fastapi import Header, HTTPException, status

from app.config import settings


async def require_api_key(x_api_key: str | None = Header(default=None)):
    if not settings.api_key:
        # Fail closed: if no key is configured on the server, refuse
        # all requests rather than silently allowing them through.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Server is not configured with an API key. Set CREDIT_INTEL_API_KEY.",
        )
    if not x_api_key or not hmac.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )
    return True
