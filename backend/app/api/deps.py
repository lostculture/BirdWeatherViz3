"""
API Dependencies
Shared dependencies for FastAPI endpoints (database, authentication, etc.).

Version: 1.0.0
"""

from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.config import settings

# Security scheme for Bearer token authentication
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Validate JWT token and return current user.

    Args:
        credentials: HTTP Bearer token credentials

    Returns:
        User information dict

    Raises:
        HTTPException: If token is invalid
    """
    token = credentials.credentials

    # TODO: Implement JWT token validation
    # For now, return a placeholder
    # In production, decode JWT and validate

    return {"username": "admin"}


def verify_config_password(password: str) -> bool:
    """
    Verify configuration password.

    Args:
        password: Password to verify

    Returns:
        True if password is correct
    """
    return password == settings.CONFIG_PASSWORD


async def get_db_dependency() -> Generator[Session, None, None]:
    """
    Get database session dependency.

    Yields:
        Database session
    """
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()
