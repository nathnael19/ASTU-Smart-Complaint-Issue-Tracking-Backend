from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr

from app.core.supabase import supabase_client, supabase_admin
from app.models.enums import UserRole
from app.dependencies import get_current_user

router = APIRouter()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: UserRole = UserRole.STUDENT
    department_name: Optional[str] = None


@router.post("/register", summary="Register a new user")
async def register(payload: SignUpRequest):
    """Register via Supabase Auth and create a profile in the users table."""
    try:
        # 1. Sign up with Supabase Auth
        clean_email = payload.email.strip().lower()
        print(f"DEBUG: Registering user with email: '{clean_email}'")
        auth_response = supabase_client.auth.sign_up(
            {"email": clean_email, "password": payload.password}
        )
        
        if not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed"
            )

        user_id = auth_response.user.id
        
        # 2. Handle Name Splitting
        name_parts = payload.full_name.strip().split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        # 3. Resolve Department ID if provided
        department_id = None
        if payload.department_name:
            dep_res = supabase_client.table("departments").select("id").eq("name", payload.department_name).execute()
            if dep_res.data:
                department_id = dep_res.data[0]["id"]

        # 4. Create User Profile
        user_data = {
            "id": user_id,
            "email": clean_email,
            "first_name": first_name,
            "last_name": last_name,
            "role": payload.role,
            "department_id": department_id,
            "status": "Active"
        }
        
        supabase_admin.table("users").insert(user_data).execute()

        return {"message": "Registration successful. Please check your email for verification.", "user_id": user_id}

    except Exception as e:
        # If user registration succeeded but profile creation failed, we might want to handle that,
        # but for now, we'll just return the error.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post("/login", summary="Sign in with email and password")
async def login(payload: LoginRequest):
    """Authenticate via Supabase Auth."""
    try:
        response = supabase_client.auth.sign_in_with_password(
            {"email": payload.email, "password": payload.password}
        )
        session = response.session
        user = response.user

        # Fetch additional profile info (like role) from our users table
        profile_res = supabase_admin.table("users").select("*").eq("id", user.id).single().execute()
        profile = profile_res.data

        return {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "token_type": "bearer",
            "expires_in": session.expires_in,
            "user": {
                "id": user.id,
                "email": user.email,
                "role": profile.get("role") if profile else "STUDENT",
                "full_name": profile.get("full_name") if profile else "",
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        ) from e


@router.post("/logout", summary="Sign out (invalidate session globally)")
async def logout(current_user: dict = Depends(get_current_user)):
    """Sign out the user and revoke all their sessions on Supabase."""
    try:
        user_id = current_user.get("sub")
        # In Supabase auth, admin.sign_out(user_id) signs out the user across all devices/sessions
        supabase_admin.auth.admin.sign_out(user_id)
        return {"message": "Logged out successfully from all devices"}
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
