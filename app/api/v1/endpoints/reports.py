from fastapi import APIRouter, Depends
from typing import List, Optional
from datetime import datetime
from app.core.supabase import supabase_admin
from app.dependencies import require_staff_or_admin

router = APIRouter()

@router.get("/department", summary="Get recent department reports")
async def get_department_reports(profile: dict = Depends(require_staff_or_admin)):
    """
    Returns the latest generated reports for the staff's department.
    """
    department_id = profile.get("department_id")
    
    if not department_id and profile.get("role") != "ADMIN":
        return []

    # Fetch reports for the department
    res = supabase_admin.table("reports").select("*")\
        .eq("department_id", department_id)\
        .order("created_at", desc=True)\
        .limit(20)\
        .execute()
    
    return res.data or []
