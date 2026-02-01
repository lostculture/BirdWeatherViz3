"""
API Dependencies
Shared dependencies for FastAPI endpoints (database, authentication, etc.).

Version: 1.0.0
"""

from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import jwt
import bcrypt

from app.db.session import get_db
from app.config import settings

# Security scheme for Bearer token authentication
security = HTTPBearer()

# Password setting key in database
PASSWORD_SETTING_KEY = "config_password_hash"


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Validate JWT token and return current user.

    Args:
        credentials: HTTP Bearer token credentials

    Returns:
        User information dict with username

    Raises:
        HTTPException: If token is invalid or expired
    """
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        username = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return {"username": username}
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_stored_password_hash() -> Optional[str]:
    """
    Get the stored password hash from the database.

    Returns:
        Password hash string if stored, None otherwise
    """
    from app.db.models.setting import Setting

    db = next(get_db())
    try:
        setting = db.query(Setting).filter(Setting.key == PASSWORD_SETTING_KEY).first()
        if setting and setting.value:
            return setting.value
        return None
    finally:
        db.close()


def set_password_hash(password: str) -> str:
    """
    Hash a password and store it in the database.

    Args:
        password: Plain text password to hash and store

    Returns:
        The generated password hash
    """
    from app.db.models.setting import Setting

    # Generate bcrypt hash
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(password_bytes, salt).decode('utf-8')

    db = next(get_db())
    try:
        setting = db.query(Setting).filter(Setting.key == PASSWORD_SETTING_KEY).first()
        if setting:
            setting.value = password_hash
        else:
            setting = Setting(
                key=PASSWORD_SETTING_KEY,
                value=password_hash,
                data_type="str",
                description="Hashed configuration password (bcrypt)"
            )
            db.add(setting)
        db.commit()
        return password_hash
    finally:
        db.close()


def verify_config_password(password: str) -> bool:
    """
    Verify configuration password.

    Checks database for stored hash first, falls back to CONFIG_PASSWORD env var.

    Args:
        password: Password to verify

    Returns:
        True if password is correct
    """
    # First check if there's a stored password hash in the database
    stored_hash = get_stored_password_hash()

    if stored_hash:
        # Verify against stored bcrypt hash
        try:
            password_bytes = password.encode('utf-8')
            stored_hash_bytes = stored_hash.encode('utf-8')
            return bcrypt.checkpw(password_bytes, stored_hash_bytes)
        except Exception:
            return False
    else:
        # Fall back to environment variable (plain text comparison)
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
