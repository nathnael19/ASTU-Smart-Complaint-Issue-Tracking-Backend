from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.supabase import supabase_admin
from app.models.enums import UserRole
from app.dependencies import get_current_user_profile, require_admin, require_staff_or_admin

router = APIRouter()


# ── GET /users/me ─────────────────────────────────────────────────────────────
@router.get("/me", summary="Get current user profile")
async def get_me(profile: dict = Depends(get_current_user_profile)):
    return profile


# ── GET /users ─────────────────────────────────────────────────────────────────
@router.get("/", summary="List all users (Admin only)")
async def list_users(
    role: Optional[str] = Query(None, description="Filter by role: STUDENT, STAFF, ADMIN"),
    status: Optional[str] = Query(None, description="Filter by status: Active, Inactive"),
    department_id: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    _admin: dict = Depends(require_admin),
):
    query = supabase_admin.table("users").select("*").is_("deleted_at", "null")
    if role:
        query = query.eq("role", role)
    if status:
        query = query.eq("status", status)
    if department_id:
        query = query.eq("department_id", department_id)
    response = query.range(offset, offset + limit - 1).execute()
    return {"data": response.data, "total": len(response.data)}


# ── GET /users/{user_id} ───────────────────────────────────────────────────────
@router.get("/{user_id}", summary="Get a user by ID (Staff/Admin only)")
async def get_user(
    user_id: str,
    _staff: dict = Depends(require_staff_or_admin),
):
    response = supabase_admin.table("users").select("*").eq("id", user_id).single().execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="User not found")
    return response.data


# ── PATCH /users/{user_id} ─────────────────────────────────────────────────────
class UpdateUserPayload(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    professional_title: Optional[str] = None
    office_location: Optional[str] = None
    student_id_number: Optional[str] = None
    program: Optional[str] = None
    avatar_url: Optional[str] = None
    status: Optional[str] = None
    department_id: Optional[str] = None


class AdminCreateUserPayload(BaseModel):
    email: str
    password: str
    full_name: str
    role: UserRole
    department_id: Optional[str] = None
    student_id_number: Optional[str] = None
    program: Optional[str] = None
    phone: Optional[str] = None
    professional_title: Optional[str] = None
    office_location: Optional[str] = None


@router.post("/admin-create", summary="Create a new user (Admin only)")
async def admin_create_user(
    payload: AdminCreateUserPayload,
    _admin: dict = Depends(require_admin),
):
    """Admin-only: Create a new user in Supabase Auth and then create their profile."""
    try:
        # 1. Create user in Supabase Auth via Admin API
        auth_response = supabase_admin.auth.admin.create_user({
            "email": payload.email.strip().lower(),
            "password": payload.password,
            "email_confirm": True  # Admins don't need to verify for created staff
        })
        
        if not auth_response.user:
            raise HTTPException(status_code=400, detail="Auth account creation failed")
            
        user_id = auth_response.user.id
        
        # 2. Handle Name Splitting
        name_parts = payload.full_name.strip().split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        
        # 3. Create Profile
        user_data = {
            "id": user_id,
            "email": payload.email.strip().lower(),
            "first_name": first_name,
            "last_name": last_name,
            "role": payload.role,
            "department_id": payload.department_id,
            "student_id_number": payload.student_id_number,
            "program": payload.program,
            "phone": payload.phone,
            "professional_title": payload.professional_title,
            "office_location": payload.office_location,
            "status": "Active"
        }
        
        profile_response = supabase_admin.table("users").insert(user_data).execute()
        return profile_response.data[0] if profile_response.data else {}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{user_id}", summary="Update a user (Admin or self)")
async def update_user(
    user_id: str,
    payload: UpdateUserPayload,
    current_profile: dict = Depends(get_current_user_profile),
):
    # Allow self-update or admin update
    if current_profile["id"] != user_id and current_profile["role"] != "ADMIN":
        raise HTTPException(status_code=403, detail="Cannot update another user's profile")
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    response = supabase_admin.table("users").update(updates).eq("id", user_id).execute()
    return response.data[0] if response.data else {}
