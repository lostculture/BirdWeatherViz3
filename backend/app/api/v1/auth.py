"""
Authentication API Endpoints
Endpoints for user authentication and token management.

Version: 1.0.0
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, status, Request, Depends
from pydantic import BaseModel
import jwt

from app.config import settings
from app.api.deps import verify_config_password, set_password_hash, get_current_user, get_stored_password_hash
from app.core.rate_limit import limiter

router = APIRouter()


class LoginRequest(BaseModel):
    """Login request model."""
    password: str


class ChangePasswordRequest(BaseModel):
    """Change password request model."""
    current_password: str
    new_password: str


class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class PasswordStatusResponse(BaseModel):
    """Password status response model."""
    is_custom: bool
    message: str


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(request: Request, login_request: LoginRequest):
    """
    Authenticate with configuration password and receive JWT token.

    Rate limited to 5 attempts per minute to prevent brute force attacks.

    Args:
        request: FastAPI request object (for rate limiting)
        login_request: Login request containing password

    Returns:
        TokenResponse with JWT access token

    Raises:
        HTTPException: If password is invalid
    """
    if not verify_config_password(login_request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate JWT token
    now = datetime.utcnow()
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = now + expires_delta

    payload = {
        "sub": "config_admin",
        "iat": now,
        "exp": expire,
    }

    access_token = jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # seconds
    )


@router.post("/logout")
async def logout():
    """
    Logout endpoint (client-side token removal).

    This is a no-op on the server side since we're using stateless JWTs.
    The client should remove the token from localStorage.

    Returns:
        Success message
    """
    return {"success": True, "message": "Logged out successfully"}


@router.get("/password-status", response_model=PasswordStatusResponse)
async def get_password_status(current_user: dict = Depends(get_current_user)):
    """
    Check if a custom password has been set.

    Returns:
        PasswordStatusResponse indicating if custom password is set
    """
    stored_hash = get_stored_password_hash()
    if stored_hash:
        return PasswordStatusResponse(
            is_custom=True,
            message="Custom password is set and stored in database"
        )
    else:
        return PasswordStatusResponse(
            is_custom=False,
            message="Using default password from environment variable"
        )


@router.put("/password")
@limiter.limit("3/minute")
async def change_password(
    request: Request,
    password_request: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Change the configuration password.

    Requires current password for verification and stores new password hash in database.
    Rate limited to 3 attempts per minute.

    Args:
        request: FastAPI request object (for rate limiting)
        password_request: ChangePasswordRequest with current and new passwords
        current_user: Authenticated user

    Returns:
        Success message

    Raises:
        HTTPException: If current password is invalid or new password is too short
    """
    # Verify current password
    if not verify_config_password(password_request.current_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )

    # Validate new password
    if len(password_request.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters long"
        )

    # Store new password hash
    set_password_hash(password_request.new_password)

    return {"success": True, "message": "Password changed successfully"}
