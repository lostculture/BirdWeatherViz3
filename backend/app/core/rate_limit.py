"""
Rate Limiting Configuration
Provides rate limiting for API endpoints.

Version: 1.0.0
"""

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def get_real_ip(request: Request) -> str:
    """Get real client IP, supporting Cloudflare and standard reverse proxies."""
    # Cloudflare provides the real IP in CF-Connecting-IP header
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip
    # Standard reverse proxy header
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


# Rate limiter instance - shared across the application
limiter = Limiter(key_func=get_real_ip)
