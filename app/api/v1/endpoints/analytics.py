from fastapi import APIRouter, Depends
from typing import List, Dict, Any
from datetime import datetime, timedelta, timezone
from app.core.supabase import supabase_admin
from app.dependencies import require_admin
from app.models.enums import ComplaintStatus

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
