from fastapi import APIRouter, Depends
from app.core.supabase import supabase_admin
from app.dependencies import get_current_user_profile, require_admin

router = APIRouter()


@router.get("/", summary="List all departments")
async def list_departments(_=Depends(get_current_user_profile)):
    response = supabase_admin.table("departments").select("*").order("name").execute()
    return response.data


@router.get("/{department_id}", summary="Get a single department")
async def get_department(department_id: str, _=Depends(get_current_user_profile)):
    from fastapi import HTTPException
    response = supabase_admin.table("departments").select("*").eq("id", department_id).single().execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Department not found")
    return response.data
