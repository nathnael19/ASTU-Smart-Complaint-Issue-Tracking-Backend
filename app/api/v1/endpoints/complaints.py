from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.supabase import supabase_admin
from app.dependencies import get_current_user_profile, require_staff_or_admin, require_admin

router = APIRouter()


# ── GET /complaints ─────────────────────────────────────────────────────────────
@router.get("/", summary="List complaints")
async def list_complaints(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    department_id: Optional[str] = Query(None),
    assigned_to: Optional[str] = Query(None),
    submitted_by: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    profile: dict = Depends(get_current_user_profile),
):
    query = supabase_admin.table("complaints").select(
        "*, users!submitted_by(full_name, email, role), departments(name)"
    ).is_("deleted_at", "null")

    # Role-based filtering
    if profile["role"] == "STUDENT":
        query = query.eq("submitted_by", profile["id"])
    elif profile["role"] == "STAFF":
        query = query.or_(f"assigned_to.eq.{profile['id']},department_id.eq.{profile.get('department_id', '')}")

    if status:
        query = query.eq("status", status)
    if priority:
        query = query.eq("priority", priority)
    if category:
        query = query.eq("category", category)
    if department_id and profile["role"] == "ADMIN":
        query = query.eq("department_id", department_id)
    if assigned_to and profile["role"] in ("STAFF", "ADMIN"):
        query = query.eq("assigned_to", assigned_to)
    if submitted_by and profile["role"] in ("STAFF", "ADMIN"):
        query = query.eq("submitted_by", submitted_by)

    response = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    return {"data": response.data, "total": len(response.data)}


# ── GET /complaints/{id} ───────────────────────────────────────────────────────
@router.get("/{complaint_id}", summary="Get a single complaint")
async def get_complaint(
    complaint_id: str,
    profile: dict = Depends(get_current_user_profile),
):
    response = supabase_admin.table("complaints").select("*").eq("id", complaint_id).single().execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Complaint not found")
    c = response.data
    # Access control
    if profile["role"] == "STUDENT" and c["submitted_by"] != profile["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    return c


from app.models.enums import ComplaintPriority, ComplaintCategory


# ── POST /complaints ────────────────────────────────────────────────────────────
class CreateComplaintPayload(BaseModel):
    title: str
    description: str
    category: str
    priority: ComplaintPriority = ComplaintPriority.MEDIUM
    department_id: Optional[str] = None
    is_draft: bool = False
    attachment_url: Optional[str] = None


@router.post("/", summary="Submit a new complaint", status_code=201)
async def create_complaint(
    payload: CreateComplaintPayload,
    profile: dict = Depends(get_current_user_profile),
):
    import random, string
    ticket_number = "ASTU-" + "".join(random.choices(string.digits, k=4))
    
    # Map frontend categories to backend enums
    category_map = {
        "IT & Network": ComplaintCategory.IT_AND_NETWORK,
        "Facility & Maintenance": ComplaintCategory.FACILITY_AND_MAINTENANCE,
        "Academic Affairs": ComplaintCategory.ACADEMIC_AFFAIRS,
        "Student Services": ComplaintCategory.STUDENT_SERVICES,
    }
    
    # Get backend enum value, fallback to OTHER if not found
    backend_category = category_map.get(payload.category, ComplaintCategory.OTHER)
    
    data = {
        "title": payload.title,
        "description": payload.description,
        "category": backend_category,
        "priority": payload.priority.value,
        "department_id": payload.department_id,
        "is_draft": payload.is_draft,
        "attachment_url": payload.attachment_url,
        "submitted_by": profile["id"],
        "ticket_number": ticket_number,
        "status": "OPEN",
    }
    response = supabase_admin.table("complaints").insert(data).execute()
    return response.data[0] if response.data else {}


# ── POST /complaints/{id}/attachments ──────────────────────────────────────────
class CreateAttachmentPayload(BaseModel):
    file_name: str
    file_size_bytes: int
    mime_type: str
    storage_path: str


@router.post("/{complaint_id}/attachments", summary="Record a complaint attachment")
async def create_attachment(
    complaint_id: str,
    payload: CreateAttachmentPayload,
    profile: dict = Depends(get_current_user_profile),
):
    # Verify complaint ownership/access
    complaint = supabase_admin.table("complaints").select("submitted_by").eq("id", complaint_id).single().execute()
    if not complaint.data:
        raise HTTPException(status_code=404, detail="Complaint not found")
    
    if profile["role"] == "STUDENT" and complaint.data["submitted_by"] != profile["id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    data = {
        **payload.model_dump(),
        "complaint_id": complaint_id,
        "uploaded_by": profile["id"],
    }
    response = supabase_admin.table("complaint_attachments").insert(data).execute()
    return response.data[0] if response.data else {}


# ── PATCH /complaints/{id} ─────────────────────────────────────────────────────
class UpdateComplaintPayload(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[str] = None
    department_id: Optional[str] = None
    sla_deadline: Optional[str] = None
    resolved_at: Optional[str] = None


@router.patch("/{complaint_id}", summary="Update complaint (Staff/Admin)")
async def update_complaint(
    complaint_id: str,
    payload: UpdateComplaintPayload,
    profile: dict = Depends(require_staff_or_admin),
):
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    response = supabase_admin.table("complaints").update(updates).eq("id", complaint_id).execute()
    return response.data[0] if response.data else {}


# ── DELETE /complaints/{id} ────────────────────────────────────────────────────
@router.delete("/{complaint_id}", summary="Soft-delete a complaint (Admin)")
async def delete_complaint(
    complaint_id: str,
    _admin: dict = Depends(require_admin),
):
    from datetime import datetime, timezone
    supabase_admin.table("complaints").update(
        {"deleted_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", complaint_id).execute()
    return {"message": "Complaint deleted"}
