"""
Shared FastAPI dependencies.

Usage:
    from app.dependencies import get_current_user, require_admin

    @router.get("/me")
    async def me(user = Depends(get_current_user)):
        ...
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from app.core.config import settings
from app.core.supabase import supabase_client, supabase_admin

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Verify the Supabase JWT from the Authorization header using the Supabase client.
    Returns the user data for downstream dependencies.
    """
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Verify the token with Supabase - this is more robust than manual JWT decoding
        # as it doesn't require the JWT secret to be manually configured/matched.
        response = supabase_client.auth.get_user(token)
        user = response.user
        
        if not user:
            raise credentials_exception
            
        # Return a structure that matches what current code expects (JWT-like payload)
        return {
            "sub": user.id,
            "id": user.id,
            "email": user.email,
            "app_metadata": user.app_metadata,
            "user_metadata": user.user_metadata,
            "aud": user.aud
        }
    except Exception as e:
        print(f"DEBUG: Auth verification failed: {str(e)}")
        raise credentials_exception


async def get_current_user_profile(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Fetch full user profile from the `users` table."""
    user_id = current_user.get("sub")
    response = supabase_admin.table("users").select("*").eq("id", user_id).single().execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="User profile not found")
    return response.data


def require_role(*roles: str):
    """Dependency factory that restricts access to specific roles."""
    async def role_checker(profile: dict = Depends(get_current_user_profile)):
        if profile.get("role") not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role(s): {', '.join(roles)}",
            )
        return profile
    return role_checker


# Convenience role guards
require_admin = require_role("ADMIN")
require_staff_or_admin = require_role("STAFF", "ADMIN")
