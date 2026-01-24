from datetime import datetime, timezone
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
    search: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(10, le=100),
    offset: int = Query(0),
    profile: dict = Depends(get_current_user_profile),
):
    query = supabase_admin.table("complaints").select(
        "*, users!submitted_by(full_name, email, role), departments(name)",
        count="exact"
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
    
    if search:
        query = query.or_(f"title.ilike.%{search}%,ticket_number.ilike.%{search}%")
    
    if start_date:
        query = query.gte("created_at", start_date)
    if end_date:
        # Append end of day to include the entire end_date
        query = query.lte("created_at", f"{end_date}T23:59:59")

    response = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    return {"data": response.data, "total": response.count}


def _can_access_complaint(complaint: dict, profile: dict) -> bool:
    """Student: only own; Staff: assigned or same department; Admin: all."""
    if profile["role"] == "ADMIN":
        return True
    if profile["role"] == "STAFF":
        return (
            complaint.get("assigned_to") == profile["id"]
            or complaint.get("department_id") == profile.get("department_id")
        )
    if profile["role"] == "STUDENT":
        return complaint.get("submitted_by") == profile["id"]
    return False


# ── GET /complaints/{id}/remarks ──────────────────────────────────────────────
@router.get("/{complaint_id}/remarks", summary="List remarks (thread) for a complaint")
async def list_complaint_remarks(
    complaint_id: str,
    profile: dict = Depends(get_current_user_profile),
):
    complaint_res = supabase_admin.table("complaints").select("submitted_by, assigned_to, department_id").eq("id", complaint_id).single().execute()
    if not complaint_res.data:
        raise HTTPException(status_code=404, detail="Complaint not found")
    if not _can_access_complaint(complaint_res.data, profile):
        raise HTTPException(status_code=403, detail="Access denied")
    response = supabase_admin.table("complaint_remarks").select(
        "id, complaint_id, author_id, content, created_at, users!author_id(full_name, first_name, last_name, role)"
    ).eq("complaint_id", complaint_id).order("created_at", desc=False).execute()
    return {"data": response.data or []}


# ── POST /complaints/{id}/remarks ─────────────────────────────────────────────
class CreateRemarkPayload(BaseModel):
    content: str


@router.post("/{complaint_id}/remarks", summary="Post a remark on a complaint", status_code=201)
async def create_complaint_remark(
    complaint_id: str,
    payload: CreateRemarkPayload,
    profile: dict = Depends(get_current_user_profile),
):
    content = (payload.content or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Content is required")
    complaint_res = supabase_admin.table("complaints").select("submitted_by, assigned_to, department_id").eq("id", complaint_id).single().execute()
    if not complaint_res.data:
        raise HTTPException(status_code=404, detail="Complaint not found")
    if not _can_access_complaint(complaint_res.data, profile):
        raise HTTPException(status_code=403, detail="Access denied")
    row = {
        "complaint_id": complaint_id,
        "author_id": profile["id"],
        "content": content,
    }
    response = supabase_admin.table("complaint_remarks").insert(row).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to create remark")
    created = response.data[0]

    # --- Trigger Notifications ---
    try:
        author_role = profile.get("role")
        author_name = (profile.get("full_name") or f"{profile.get('first_name', '')} {profile.get('last_name', '')}").strip() or "Someone"
        ticket_number = complaint_res.data.get("ticket_number") or complaint_id[:8]
        
        notif_title = f"New message on #{ticket_number}"
        content_excerpt = content[:50] + "..." if len(content) > 50 else content
        notif_message = f"{author_name} sent a message: {content_excerpt}"
        
        recipients = []
        if author_role == "STUDENT":
            # Notify assigned staff
            if complaint_res.data.get("assigned_to"):
                recipients.append({
                    "user_id": complaint_res.data["assigned_to"],
                    "link": f"/staff/tickets/{complaint_id}"
                })
        else:
            # Staff or Admin posted, notify student
            recipients.append({
                "user_id": complaint_res.data["submitted_by"],
                "link": f"/student/complaints/{complaint_id}"
            })
            
        for recipient in recipients:
            supabase_admin.table("notifications").insert({
                "user_id": recipient["user_id"],
                "title": notif_title,
                "message": notif_message,
                "type": "chat_message",
                "link": recipient["link"],
                "is_read": False,
            }).execute()
    except Exception as e:
        # Log error but don't fail the remark creation
        print(f"Failed to send chat notification: {e}")

    # Attach author info for consistent response shape with list endpoint
    first = (profile.get("first_name") or "").strip()
    last = (profile.get("last_name") or "").strip()
    full_name = f"{first} {last}".strip() or profile.get("full_name") or "Unknown"
    author = {
        "full_name": full_name,
        "first_name": profile.get("first_name"),
        "last_name": profile.get("last_name"),
        "role": profile.get("role"),
    }
    return {**created, "users": author}


# ── GET /complaints/{id} ───────────────────────────────────────────────────────
@router.get("/{complaint_id}", summary="Get a single complaint")
async def get_complaint(
    complaint_id: str,
    profile: dict = Depends(get_current_user_profile),
):
    response = supabase_admin.table("complaints").select(
        "*, users!submitted_by(full_name, first_name, last_name, email, role, student_id_number, program, phone),"
        "assigned_user:users!assigned_to(full_name, first_name, last_name, role)"
    ).eq("id", complaint_id).single().execute()
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
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[str] = None
    department_id: Optional[str] = None
    attachment_url: Optional[str] = None
    sla_deadline: Optional[str] = None
    resolved_at: Optional[str] = None
    satisfaction_rating: Optional[int] = None
    satisfaction_message: Optional[str] = None


@router.patch("/{complaint_id}", summary="Update complaint")
async def update_complaint(
    complaint_id: str,
    payload: UpdateComplaintPayload,
    profile: dict = Depends(get_current_user_profile),
):
    # Fetch existing complaint
    response = supabase_admin.table("complaints").select("*").eq("id", complaint_id).single().execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Complaint not found")
    c = response.data

    # Access control
    if profile["role"] == "STUDENT":
        if c["submitted_by"] != profile["id"]:
            raise HTTPException(status_code=403, detail="Access denied")
        if c["status"] != "OPEN" and not (c["status"] == "RESOLVED" and (payload.satisfaction_rating is not None or payload.satisfaction_message is not None)):
            raise HTTPException(status_code=400, detail="Only OPEN complaints can be edited by students (unless providing feedback on a RESOLVED complaint)")
        # Students can only update specific fields
        updates = payload.model_dump(include={"title", "description", "category", "priority", "attachment_url", "satisfaction_rating", "satisfaction_message"}, exclude_none=True)
    else:
        # Staff/Admin can update everything in the payload
        if profile["role"] not in ("STAFF", "ADMIN"):
             raise HTTPException(status_code=403, detail="Access denied")
        updates = payload.model_dump(exclude_none=True)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    new_assigned_to = updates.get("assigned_to")
    old_assigned_to = c.get("assigned_to")
    new_status = updates.get("status")
    old_status = c.get("status")
    
    is_new_assignment = (
        profile["role"] in ("ADMIN", "STAFF")
        and new_assigned_to
        and new_assigned_to != old_assigned_to
    )

    if new_status == "RESOLVED" and not updates.get("resolved_at"):
        updates["resolved_at"] = datetime.now(timezone.utc).isoformat()

    response = supabase_admin.table("complaints").update(updates).eq("id", complaint_id).execute()
    updated = response.data[0] if response.data else {}

    if not updated:
        return {}

    ticket_number = updated.get("ticket_number") or complaint_id[:8]

    # Handle resolution notification
    if new_status == "RESOLVED" and old_status != "RESOLVED":
        try:
            supabase_admin.table("notifications").insert({
                "user_id": updated["submitted_by"],
                "title": f"Complaint Resolved: #{ticket_number}",
                "message": f"Your complaint '{updated['title']}' has been marked as resolved. Please provide your feedback.",
                "type": "STATUS_CHANGE",
                "link": f"/student/complaints/{complaint_id}",
                "is_read": False,
            }).execute()
        except Exception as e:
            print(f"Failed to send resolution notification: {e}")

    if is_new_assignment:
        # Notify the assigned staff and add a remark to the thread
        assigner_first = (profile.get("first_name") or "").strip()
        assigner_last = (profile.get("last_name") or "").strip()
        assigner_name = f"{assigner_first} {assigner_last}".strip() or profile.get("full_name") or "Admin"
        staff_res = supabase_admin.table("users").select("first_name, last_name, full_name").eq("id", new_assigned_to).single().execute()
        staff_name = "Staff"
        if staff_res.data:
            s = staff_res.data
            fn = (s.get("first_name") or "").strip()
            ln = (s.get("last_name") or "").strip()
            staff_name = f"{fn} {ln}".strip() or s.get("full_name") or staff_name
        
        notif_title = "New complaint assignment"
        notif_message = f"You have been assigned to complaint {ticket_number} by {assigner_name}."
        supabase_admin.table("notifications").insert({
            "user_id": new_assigned_to,
            "title": notif_title,
            "message": notif_message,
            "type": "assignment",
            "link": f"/staff/tickets/{complaint_id}",
            "is_read": False,
        }).execute()
        
        remark_content = f"{assigner_name} assigned {staff_name} to this complaint."
        supabase_admin.table("complaint_remarks").insert({
            "complaint_id": complaint_id,
            "author_id": profile["id"],
            "content": remark_content,
        }).execute()

    return updated


# ── DELETE /complaints/{id} ────────────────────────────────────────────────────
@router.delete("/{complaint_id}", summary="Delete a complaint")
async def delete_complaint(
    complaint_id: str,
    profile: dict = Depends(get_current_user_profile),
):
    # Fetch existing complaint
    response = supabase_admin.table("complaints").select("*").eq("id", complaint_id).single().execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Complaint not found")
    c = response.data

    # Access control
    if profile["role"] == "STUDENT":
        if c["submitted_by"] != profile["id"]:
            raise HTTPException(status_code=403, detail="Access denied")
        if c["status"] != "OPEN":
            raise HTTPException(status_code=400, detail="Only OPEN complaints can be deleted by students")
    elif profile["role"] != "ADMIN":
        raise HTTPException(status_code=403, detail="Access denied")

    from datetime import datetime, timezone
    supabase_admin.table("complaints").update(
        {"deleted_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", complaint_id).execute()
    return {"message": "Complaint deleted"}
