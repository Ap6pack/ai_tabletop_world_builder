"""
Authentication API router for user registration, login, and profile management.
"""
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.middleware.auth import require_auth
from api.services.auth_service import AuthService
from api.utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])
auth_service = AuthService()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    """Payload for user registration."""
    username: str = Field(..., min_length=3, description="Unique username")
    email: str = Field(..., description="Email address")
    password: str = Field(..., min_length=8, description="Password (min 8 chars)")
    display_name: str = Field("", description="Optional display name")


class LoginRequest(BaseModel):
    """Payload for user login."""
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")


class TokenResponse(BaseModel):
    """JWT token pair returned after login or refresh."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Public user profile."""
    id: str
    username: str
    email: str
    display_name: str
    role: str
    created_at: str


class ChangePasswordRequest(BaseModel):
    """Payload for changing a password."""
    old_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password (min 8 chars)")


class RefreshRequest(BaseModel):
    """Payload for refreshing an access token."""
    refresh_token: str = Field(..., description="Valid refresh token")


class UpdateProfileRequest(BaseModel):
    """Payload for updating a user profile."""
    display_name: Optional[str] = None
    email: Optional[str] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest) -> UserResponse:
    """Register a new user account."""
    try:
        user = auth_service.register(
            username=request.username,
            email=request.email,
            password=request.password,
            display_name=request.display_name,
        )
        return UserResponse(**user)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest) -> TokenResponse:
    """Authenticate and receive a JWT token pair."""
    user = auth_service.authenticate(request.username, request.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = auth_service.create_access_token(
        user_id=user["id"], username=user["username"], role=user.get("role", "user")
    )
    refresh_token = auth_service.create_refresh_token(user_id=user["id"])

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: RefreshRequest) -> TokenResponse:
    """Exchange a valid refresh token for a new access token."""
    payload = auth_service.verify_token(request.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub", "")
    user = auth_service.get_user(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    access_token = auth_service.create_access_token(
        user_id=user["id"], username=user["username"], role=user.get("role", "user")
    )
    refresh_token = auth_service.create_refresh_token(user_id=user["id"])

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_profile(user: Dict = Depends(require_auth)) -> UserResponse:
    """Return the current user's profile."""
    return UserResponse(**user)


@router.put("/me", response_model=UserResponse)
async def update_profile(
    request: UpdateProfileRequest,
    user: Dict = Depends(require_auth),
) -> UserResponse:
    """Update the current user's profile."""
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    updated_user = auth_service.update_user(user["id"], updates)
    if updated_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return UserResponse(**updated_user)


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    user: Dict = Depends(require_auth),
) -> Dict:
    """Change the current user's password."""
    try:
        success = auth_service.change_password(
            user_id=user["id"],
            old_password=request.old_password,
            new_password=request.new_password,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    return {"message": "Password changed successfully"}
