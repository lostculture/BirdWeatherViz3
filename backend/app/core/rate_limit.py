"""
Rate Limiting Configuration
Provides rate limiting for API endpoints.

Version: 1.0.0
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Rate limiter instance - shared across the application
limiter = Limiter(key_func=get_remote_address)
