from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, complaints, departments, notifications, analytics

api_router = APIRouter()

api_router.include_router(auth.router,        prefix="/auth",        tags=["Auth"])
api_router.include_router(users.router,       prefix="/users",       tags=["Users"])
api_router.include_router(complaints.router,  prefix="/complaints",  tags=["Complaints"])
api_router.include_router(departments.router, prefix="/departments", tags=["Departments"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
