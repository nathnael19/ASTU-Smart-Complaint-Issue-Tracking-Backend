from typing import Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from .base import UUIDModel

class ComplaintAttachmentBase(BaseModel):
    complaint_id: UUID
    uploaded_by: UUID
    file_name: str
    file_size_bytes: int
    mime_type: str
    storage_path: str

class ComplaintAttachmentCreate(ComplaintAttachmentBase):
    pass

class ComplaintAttachment(ComplaintAttachmentBase, UUIDModel):
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
