from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.supabase import supabase_admin
from app.dependencies import get_current_user_profile
from app.models.notification import Notification, NotificationUpdate

router = APIRouter()

@router.get("/", response_model=List[dict], summary="List notifications for current user")
async def list_notifications(
    limit: int = Query(20, le=100),
    offset: int = Query(0),
    profile: dict = Depends(get_current_user_profile),
):
    response = supabase_admin.table("notifications") \
        .select("*") \
        .eq("user_id", profile["id"]) \
        .order("created_at", desc=True) \
        .range(offset, offset + limit - 1) \
        .execute()
    
    return response.data

@router.patch("/{notification_id}/read", summary="Mark a notification as read")
async def mark_as_read(
    notification_id: str,
    profile: dict = Depends(get_current_user_profile),
):
    # Verify ownership
    existing = supabase_admin.table("notifications") \
        .select("user_id") \
        .eq("id", notification_id) \
        .single() \
        .execute()
    
    if not existing.data:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    if str(existing.data["user_id"]) != str(profile["id"]):
        raise HTTPException(status_code=403, detail="Access denied")

    response = supabase_admin.table("notifications") \
        .update({"is_read": True}) \
        .eq("id", notification_id) \
        .execute()
    
    return response.data[0] if response.data else {}

@router.post("/mark-all-read", summary="Mark all notifications as read")
async def mark_all_as_read(
    profile: dict = Depends(get_current_user_profile),
):
    response = supabase_admin.table("notifications") \
        .update({"is_read": True}) \
        .eq("user_id", profile["id"]) \
        .eq("is_read", False) \
        .execute()
    
    return {"message": f"Marked {len(response.data)} notifications as read"}
