from typing import Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, ConfigDict
from .enums import UserRole, UserStatus
from .base import UUIDModel, TimestampModel, SoftDeleteModel

class UserBase(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    role: UserRole = UserRole.STUDENT
    department_id: Optional[UUID] = None
    status: UserStatus = UserStatus.ACTIVE
    professional_title: Optional[str] = None
    office_location: Optional[str] = None
    student_id_number: Optional[str] = None
    program: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    avatar_seed: Optional[str] = None

class UserCreate(UserBase):
    password_hash: str

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    department_id: Optional[UUID] = None
    status: Optional[UserStatus] = None
    professional_title: Optional[str] = None
    office_location: Optional[str] = None
    student_id_number: Optional[str] = None
    program: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    avatar_seed: Optional[str] = None

class User(UserBase, UUIDModel, TimestampModel, SoftDeleteModel):
    full_name: str
    last_login_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)
