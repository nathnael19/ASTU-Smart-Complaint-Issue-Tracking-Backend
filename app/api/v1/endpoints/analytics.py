from fastapi import APIRouter, Depends
from typing import List, Dict, Any
from datetime import datetime, timedelta, timezone
from app.core.supabase import supabase_admin
from app.models.enums import ComplaintStatus
from app.dependencies import require_admin, require_staff_or_admin, get_current_user_profile

router = APIRouter()

@router.get("/summary", summary="Get dashboard summary statistics")
async def get_summary(_admin: dict = Depends(require_admin)):
    """
    Returns high-level stats for the admin dashboard.
    """
    # 1. Total Complaints
    total_res = supabase_admin.table("complaints").select("id", count="exact").is_("deleted_at", "null").execute()
    total_complaints = total_res.count or 0

    # 2. Resolved Complaints (RESOLVED + CLOSED)
    resolved_res = supabase_admin.table("complaints").select("id", count="exact")\
        .is_("deleted_at", "null")\
        .in_("status", [ComplaintStatus.RESOLVED.value, ComplaintStatus.CLOSED.value])\
        .execute()
    resolved_count = resolved_res.count or 0
    
    resolution_rate = (resolved_count / total_complaints * 100) if total_complaints > 0 else 0

    # 3. Average Resolution Time (in days)
    # This requires fetching complaints that have both created_at and resolved_at
    # For performance, we'll just sample the last 100 resolved complaints
    resolution_time_res = supabase_admin.table("complaints")\
        .select("created_at, resolved_at")\
        .is_("deleted_at", "null")\
        .not_.is_("resolved_at", "null")\
        .order("resolved_at", desc=True)\
        .limit(100)\
        .execute()
    
    avg_days = 0
    if resolution_time_res.data:
        total_days = 0
        for c in resolution_time_res.data:
            created = datetime.fromisoformat(c["created_at"].replace("Z", "+00:00"))
            resolved = datetime.fromisoformat(c["resolved_at"].replace("Z", "+00:00"))
            total_days += (resolved - created).total_seconds() / (24 * 3600)
        avg_days = round(total_days / len(resolution_time_res.data), 1)

    # 4. Active Users
    users_res = supabase_admin.table("users").select("id", count="exact").eq("status", "Active").is_("deleted_at", "null").execute()
    active_users = users_res.count or 0

    return {
        "total_complaints": total_complaints,
        "resolution_rate": f"{round(resolution_rate, 1)}%",
        "avg_resolution_time": f"{avg_days} days",
        "active_users": active_users
    }

@router.get("/categories", summary="Get complaints count by category")
async def get_category_stats(_admin: dict = Depends(require_admin)):
    """
    Returns counts grouped by category for charting.
    """
    # Supabase/PostgREST doesn't support GROUP BY directly in the client easily for counts
    # We'll fetch all non-deleted complaints' categories and count in Python
    # For a large dataset, a RPC (Remote Procedure Call) would be better
    res = supabase_admin.table("complaints").select("category").is_("deleted_at", "null").execute()
    
    counts: Dict[str, int] = {}
    for item in res.data:
        cat = item["category"]
        counts[cat] = counts.get(cat, 0) + 1
        
    return [{"category": k, "count": v} for k, v in counts.items()]

@router.get("/trends", summary="Get complaint volume trends (last 6 months)")
async def get_trend_stats(_admin: dict = Depends(require_admin)):
    """
    Returns monthly complaint counts for the last 6 months.
    """
    # Fetch created_at for all complaints in the last 6 months
    six_months_ago = (datetime.now(timezone.utc) - timedelta(days=180)).isoformat()
    res = supabase_admin.table("complaints").select("created_at")\
        .is_("deleted_at", "null")\
        .gte("created_at", six_months_ago)\
        .execute()
    
    # Group by Month
    trends: Dict[str, int] = {}
    for item in res.data:
        dt = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
        month_key = dt.strftime("%b").upper() # "JAN", "FEB", etc.
        trends[month_key] = trends.get(month_key, 0) + 1
    
    # Ensure all last 6 months are represented (optional but good for charts)
    result = []
    for i in range(5, -1, -1):
        m = (datetime.now(timezone.utc) - timedelta(days=i*30)).strftime("%b").upper()
        result.append({"month": m, "count": trends.get(m, 0)})
        
    return result

@router.get("/department/summary", summary="Get department summary statistics")
async def get_department_summary(profile: dict = Depends(require_staff_or_admin)):
    """
    Returns high-level stats for the staff dashboard based on department.
    """
    department_id = profile.get("department_id")
    user_id = profile.get("id")

    if not department_id and profile.get("role") != "ADMIN":
        return {
            "assigned_tickets": 0,
            "pending_dept_tasks": 0,
            "avg_response_time": "0 hrs",
            "resolved_this_week": 0
        }

    # 1. Assigned Tickets (to the specific user)
    assigned_res = supabase_admin.table("complaints").select("id", count="exact")\
        .eq("assigned_to", user_id)\
        .is_("deleted_at", "null")\
        .in_("status", [ComplaintStatus.OPEN.value, ComplaintStatus.IN_PROGRESS.value])\
        .execute()
    assigned_tickets = assigned_res.count or 0

    # 2. Pending Dept Tasks (for the whole department)
    pending_res = supabase_admin.table("complaints").select("id", count="exact")\
        .eq("department_id", department_id)\
        .is_("deleted_at", "null")\
        .in_("status", [ComplaintStatus.OPEN.value, ComplaintStatus.IN_PROGRESS.value])\
        .execute()
    pending_dept_tasks = pending_res.count or 0

    # 3. Average Response Time (for the department, in hours)
    # Estimate based on created_at vs resolved_at for recent tickets
    resolution_time_res = supabase_admin.table("complaints")\
        .select("created_at, resolved_at")\
        .eq("department_id", department_id)\
        .is_("deleted_at", "null")\
        .not_.is_("resolved_at", "null")\
        .order("resolved_at", desc=True)\
        .limit(50)\
        .execute()
    
    avg_hrs = 0
    if resolution_time_res.data:
        total_hrs = 0
        for c in resolution_time_res.data:
            created = datetime.fromisoformat(c["created_at"].replace("Z", "+00:00"))
            resolved = datetime.fromisoformat(c["resolved_at"].replace("Z", "+00:00"))
            total_hrs += (resolved - created).total_seconds() / 3600
        avg_hrs = round(total_hrs / len(resolution_time_res.data), 1)

    # 4. Resolved this week (for the department)
    one_week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    resolved_week_res = supabase_admin.table("complaints").select("id", count="exact")\
        .eq("department_id", department_id)\
        .is_("deleted_at", "null")\
        .in_("status", [ComplaintStatus.RESOLVED.value, ComplaintStatus.CLOSED.value])\
        .gte("resolved_at", one_week_ago)\
        .execute()
    resolved_this_week = resolved_week_res.count or 0

    return {
        "assigned_tickets": assigned_tickets,
        "pending_dept_tasks": pending_dept_tasks,
        "avg_response_time": f"{avg_hrs} hrs",
        "resolved_this_week": resolved_this_week
    }

@router.get("/department/trends", summary="Get department ticket volume trends (last 7 days)")
async def get_department_trends(profile: dict = Depends(require_staff_or_admin)):
    """
    Returns daily ticket counts for the last 7 days for the staff's department.
    """
    department_id = profile.get("department_id")
    
    if not department_id and profile.get("role") != "ADMIN":
        return []

    # Fetch created_at for department complaints in the last 7 days
    seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    res = supabase_admin.table("complaints").select("created_at")\
        .eq("department_id", department_id)\
        .is_("deleted_at", "null")\
        .gte("created_at", seven_days_ago)\
        .execute()
    
    # Group by Day
    trends: Dict[str, int] = {}
    for item in res.data:
        dt = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
        day_key = dt.strftime("%A")[:3].upper() # "MON", "TUE", etc.
        trends[day_key] = trends.get(day_key, 0) + 1
    
    # Ensure all last 7 days are represented in order
    result = []
    # Start from 6 days ago up to today
    for i in range(6, -1, -1):
        d = (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%A")[:3].upper()
        # Find if we already added it (in case of duplicate day names over week boundary)
        # We can just append and it represents the sequence
        result.append({"day": d, "value": trends.get(d, 0)})
        
    return result
