from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.config import settings
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
    query = supabase_admin.table("users").select("*", count="exact").is_("deleted_at", "null").neq("id", _admin["id"])
    if role:
        query = query.eq("role", role)
    if status:
        query = query.eq("status", status)
    if department_id:
        query = query.eq("department_id", department_id)

    response = query.range(offset, offset + limit - 1).execute()
    users = list(response.data or [])
    total_count = response.count if hasattr(response, 'count') else len(users)

    # When there are no other users, include the current admin so they see themselves
    if not users:
        users = [_admin]
        total_count = 1

    # Pre-fetch counts for students and staff
    for user in users:
        if user.get("role") == "STUDENT":
            # fetch total complaints
            count_res = supabase_admin.table("complaints").select("id", count="exact").eq("submitted_by", user["id"]).execute()
            user["total_complaints"] = count_res.count if hasattr(count_res, 'count') else 0
        elif user.get("role") == "STAFF":
            # fetch total resolved complaints assigned to this staff
            count_res = supabase_admin.table("complaints").select("id", count="exact").eq("assigned_to", user["id"]).eq("status", "RESOLVED").execute()
            user["total_resolved_complaints"] = count_res.count if hasattr(count_res, 'count') else 0

    return {"data": users, "total": total_count}


@router.get("/department", summary="List users in current department (Staff/Admin)")
async def get_department_users(profile: dict = Depends(require_staff_or_admin)):
    dept_id = profile.get("department_id")
    if not dept_id:
        # If admin has no dept, they might want all or nothing. 
        # For simplicity, if no dept, return empty or all admins.
        if profile["role"] == "ADMIN":
            query = supabase_admin.table("users").select("*").eq("role", "ADMIN").is_("deleted_at", "null")
        else:
            return {"data": [], "total": 0}
    else:
        query = supabase_admin.table("users").select("*").eq("department_id", dept_id).is_("deleted_at", "null")
    
    response = query.order("full_name").execute()
    users = response.data or []
    
    # Add ticket counts
    for user in users:
        if user.get("role") == "STAFF":
            # Active tasks (OPEN or IN_PROGRESS)
            active_res = supabase_admin.table("complaints").select("id", count="exact")\
                .eq("assigned_to", user["id"])\
                .in_("status", ["OPEN", "IN_PROGRESS"])\
                .is_("deleted_at", "null")\
                .execute()
            user["active_tickets_count"] = active_res.count or 0
            
            # Resolved tasks
            resolved_res = supabase_admin.table("complaints").select("id", count="exact")\
                .eq("assigned_to", user["id"])\
                .eq("status", "RESOLVED")\
                .is_("deleted_at", "null")\
                .execute()
            user["resolved_tickets_count"] = resolved_res.count or 0

    return {"data": users, "total": len(users)}


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


# ── GET /users/by-id-number/{id_number} ───────────────────────────────────────
@router.get("/by-id-number/{id_number}", summary="Get a user by ID Number (Staff/Admin only)")
async def get_user_by_id_number(
    id_number: str,
    _staff: dict = Depends(require_staff_or_admin),
):
    # Decode URL encoded ID numbers (e.g. ugr/31038/15 becomes encoded as ugr%2F31038%2F15)
    from urllib.parse import unquote
    decoded_id = unquote(id_number)
    
    response = supabase_admin.table("users").select("*").eq("student_id_number", decoded_id).is_("deleted_at", "null").execute()
    
    if not response.data:
        raise HTTPException(status_code=404, detail="User not found")
    
    return response.data[0]


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
    full_name: str
    role: UserRole
    department_id: Optional[str] = None
    student_id_number: Optional[str] = None
    program: Optional[str] = None
    phone: Optional[str] = None
    professional_title: Optional[str] = None
    office_location: Optional[str] = None


@router.post("/admin-create", summary="Create a new user/staff via email invite (Admin only)")
async def admin_create_user(
    payload: AdminCreateUserPayload,
    _admin: dict = Depends(require_admin),
):
    """Admin-only: Invite a new user via Supabase Auth and then create their profile."""
    try:
        # 1. Invite user in Supabase Auth via Admin API
        # Email link will redirect to /new-password with tokens in URL hash so they can set a password
        set_password_url = f"{settings.FRONTEND_URL}/new-password"
        auth_response = supabase_admin.auth.admin.invite_user_by_email(
            payload.email.strip().lower(),
            options={
                "data": {"role": payload.role},
                "redirect_to": set_password_url,
                "redirectTo": set_password_url,  # some clients use camelCase
            }
        )
        
        if not hasattr(auth_response, 'user') or not auth_response.user:
            raise HTTPException(status_code=400, detail="Auth account invitation failed")
            
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


@router.delete("/{user_id}", summary="Delete a user (Admin only)")
async def delete_user(
    user_id: str,
    admin_profile: dict = Depends(require_admin),
):
    """Admin-only: Permanently delete a user from the system and auth database."""
    # Prevent admin from deleting themselves
    if admin_profile["id"] == user_id:
        raise HTTPException(status_code=400, detail="Admins cannot delete their own account")
        
    try:
        # 1. Delete from public users table (Handles app-level cascading if defined in DB)
        profile_response = supabase_admin.table("users").delete().eq("id", user_id).execute()
        
        # 2. Delete from Supabase Auth (This is the ultimate source of truth for logins)
        auth_response = supabase_admin.auth.admin.delete_user(user_id)
        
        return {"detail": "User deleted successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to delete user: {str(e)}")
