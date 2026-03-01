from typing import Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from .enums import ComplaintStatus, ComplaintPriority, ComplaintCategory
from .base import UUIDModel, TimestampModel, SoftDeleteModel

class ComplaintBase(BaseModel):
    title: str
    description: str
    category: ComplaintCategory
    priority: ComplaintPriority = ComplaintPriority.MEDIUM
    status: ComplaintStatus = ComplaintStatus.OPEN
    submitted_by: UUID
    assigned_to: Optional[UUID] = None
    department_id: Optional[UUID] = None
    sla_deadline: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    is_draft: bool = False
    satisfaction_rating: Optional[int] = Field(None, ge=1, le=5)
    satisfaction_message: Optional[str] = None

class ComplaintCreate(ComplaintBase):
    ticket_number: str

class ComplaintUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[ComplaintCategory] = None
    priority: Optional[ComplaintPriority] = None
    status: Optional[ComplaintStatus] = None
    assigned_to: Optional[UUID] = None
    department_id: Optional[UUID] = None
    sla_deadline: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    is_draft: Optional[bool] = None
    satisfaction_rating: Optional[int] = Field(None, ge=1, le=5)
    satisfaction_message: Optional[str] = None

class Complaint(ComplaintBase, UUIDModel, TimestampModel, SoftDeleteModel):
    ticket_number: str
    
    model_config = ConfigDict(from_attributes=True)
