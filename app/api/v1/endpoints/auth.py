from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.core.supabase import supabase_client, supabase_admin

router = APIRouter()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str


@router.post("/login", summary="Sign in with email and password")
async def login(payload: LoginRequest):
    """Authenticate via Supabase Auth."""
    try:
        response = supabase_client.auth.sign_in_with_password(
            {"email": payload.email, "password": payload.password}
        )
        session = response.session
        return {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "token_type": "bearer",
            "expires_in": session.expires_in,
            "user": {
                "id": response.user.id,
                "email": response.user.email,
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        ) from e


@router.post("/logout", summary="Sign out (invalidate session)")
async def logout(refresh_token: str):
    """Sign out and revoke the refresh token on Supabase."""
    try:
        supabase_client.auth.sign_out()
        return {"message": "Logged out successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/refresh", summary="Refresh access token")
async def refresh_token(refresh_token: str):
    """Exchange a refresh token for a new access token."""
    try:
        response = supabase_client.auth.refresh_session(refresh_token)
        session = response.session
        return {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "token_type": "bearer",
            "expires_in": session.expires_in,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid refresh token") from e
