from typing import Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from .base import UUIDModel

class ComplaintAssignmentBase(BaseModel):
    complaint_id: UUID
    assigned_to: Optional[UUID] = None
    assigned_by: Optional[UUID] = None
    note: Optional[str] = None
    assigned_at: datetime = Field(default_factory=datetime.now)
    unassigned_at: Optional[datetime] = None

class ComplaintAssignmentCreate(ComplaintAssignmentBase):
    pass

class ComplaintAssignment(ComplaintAssignmentBase, UUIDModel):
    model_config = ConfigDict(from_attributes=True)
