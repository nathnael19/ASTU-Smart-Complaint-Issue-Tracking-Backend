from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.supabase import supabase_admin
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
    avatar_url: Optional[str] = None
    status: Optional[str] = None
    department_id: Optional[str] = None


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
